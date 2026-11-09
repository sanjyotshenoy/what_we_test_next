"""Per-browser request accounting without visitor admission or session limits."""
from collections import deque
import secrets
import time

from aiohttp import web

COOKIE = 'demo_visitor'


class VisitorRequests:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.buckets = {}

    @web.middleware
    async def middleware(self, request, handler):
        metered = request.path in {'/', '/planner', '/results', '/sequential'} or (
            request.path.startswith('/api/') and request.path != '/api/health'
            and not request.path.endswith('/stop'))
        if not metered:
            return await handler(request)
        now = self.clock()
        # Discard only obsolete rate accounting. This never expires access or
        # reserves a visitor slot; any browser can immediately make a new request.
        for token, bucket in list(self.buckets.items()):
            if not bucket or bucket[-1] < now - 60:
                del self.buckets[token]
        token = request.cookies.get(COOKIE)
        if token not in self.buckets:
            token = secrets.token_hex(32)
            self.buckets[token] = deque()
        request['visitor_requests'] = self.buckets[token]
        response = await handler(request)
        response.set_cookie(COOKIE, token, httponly=True, samesite='Strict', path='/',
                            secure=request.host.split(':')[0] not in ('localhost', '127.0.0.1'))
        return response
