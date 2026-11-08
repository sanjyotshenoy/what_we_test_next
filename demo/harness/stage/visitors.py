"""Bounded browser-session admission for the public dashboard."""
from collections import deque
import secrets
import time

from aiohttp import web

COOKIE = 'demo_visitor'
BUSY = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15"><title>Project Ouroboros — Demo busy</title>
<body style="background:#101820;color:#eef4f7;font:18px system-ui;max-width:38rem;margin:15vh auto;padding:24px">
<h1>The demo is currently full</h1><p>All 30 dashboard visitor slots are in use.
This page will retry automatically every 15 seconds as slots become available.</p>
<p><a href="" style="color:#80dfcf">Try again now</a></p></body></html>'''


class Visitors:
    def __init__(self, limit=30, ttl=120, clock=time.monotonic):
        self.limit, self.ttl, self.clock = limit, ttl, clock
        self.sessions = {}

    @web.middleware
    async def middleware(self, request, handler):
        # Stopping an owned model must remain possible even when admission expires.
        guarded = request.path in {'/', '/planner', '/results', '/sequential'} or (
            request.path.startswith('/api/') and request.path != '/api/health'
            and not request.path.endswith('/stop'))
        if not guarded:
            return await handler(request)
        now = self.clock()
        for token, entry in list(self.sessions.items()):
            if now - entry['seen'] >= self.ttl:
                del self.sessions[token]
        token = request.cookies.get(COOKIE)
        if token not in self.sessions:
            if len(self.sessions) >= self.limit:
                return web.Response(status=429, text=BUSY if not request.path.startswith('/api/') else 'Dashboard full. Please retry shortly.',
                                    content_type='text/html' if not request.path.startswith('/api/') else 'text/plain',
                                    headers={'Retry-After': '15', 'Cache-Control': 'no-store'})
            token = secrets.token_hex(32)
            self.sessions[token] = {'seen': now, 'requests': deque()}
        entry = self.sessions[token]
        entry['seen'] = now
        request['visitor_requests'] = entry['requests']
        response = await handler(request)
        response.set_cookie(COOKIE, token, httponly=True, samesite='Strict', path='/',
                            secure=request.host.split(':')[0] not in ('localhost', '127.0.0.1'))
        return response
