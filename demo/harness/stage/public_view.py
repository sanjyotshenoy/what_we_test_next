"""Explicitly published results only. Bind behind the authenticated HTTPS proxy.

This service has no OpenCode connection and cannot launch or change experiments.
"""
import asyncio
from collections import deque
import json
import os
from pathlib import Path
import time

from aiohttp import web
from demo.harness.stage import planning_view, recording

STATIC = Path(__file__).parent / 'static'
DEMO_STATIC = Path(__file__).resolve().parents[2]
SEQUENTIAL_FILES = {'demo.css', 'sequential.css', 'sequential.js',
                    'fonts/Lato-Regular.woff2', 'fonts/Lato-Semibold.woff2', 'fonts/Lato-Bold.woff2'}
STATIC_FILES = {'planner.css', 'planner.js'}
DOWNLOAD_FILES = planning_view.BATCH_FILES | (planning_view.RUN_FILES - {'simulator.log'})


def make_app(published, *, request_limit=600):
    published = tuple(published)
    if not published or any(not planning_view.TOKEN.fullmatch(s) for s in published):
        raise ValueError('Explicit published session IDs are required')
    requests = deque()
    cache = {}
    lock = asyncio.Lock()

    @web.middleware
    async def boundary(request, handler):
        now = time.monotonic()
        while requests and requests[0] < now - 60:
            requests.popleft()
        if len(requests) >= request_limit:
            return web.Response(status=429, text='Please wait before refreshing.', headers={'Retry-After': '60'})
        requests.append(now)
        if request.method not in {'GET', 'HEAD'}:
            return web.Response(status=405, text='This results viewer is read-only.')
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = web.Response(status=exc.status, text=exc.reason)
        except Exception:
            response = web.Response(status=503, text='Results temporarily unavailable.')
        response.headers.update({
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        })
        return response

    async def index(request):
        return web.FileResponse(STATIC / 'planner.html')

    async def static(request):
        name = request.match_info['name']
        if name not in STATIC_FILES:
            raise web.HTTPNotFound()
        return web.FileResponse(STATIC / name)

    async def sequential(request):
        return web.FileResponse(DEMO_STATIC / 'sequential.html')

    async def sequential_asset(request):
        name = request.match_info['name']
        if name not in SEQUENTIAL_FILES:
            raise web.HTTPNotFound()
        return web.FileResponse(DEMO_STATIC / name)

    async def health(request):
        return web.json_response({'ok': True, 'opencode': False, 'replay': True,
                                  'read_only': True, 'default_session': published[0]})

    async def models(request):
        return web.json_response({'models': [], 'current': {}, 'replay': True})

    async def sessions(request):
        result = []
        for s in published:
            data = await snapshot(s)
            result.append({'session': s, 'run_count': sum(len(b['manifest'].get('runs', []))
                                                         for b in data['batches'])})
        return web.json_response(result)

    async def snapshot(session):
        async with lock:
            now = time.monotonic()
            if session not in cache or now - cache[session][0] > 2:
                data = await asyncio.to_thread(planning_view.snapshot, session)
                cache[session] = (now, data)
            return cache[session][1]

    async def planning(request):
        session = request.query.get('session', published[0])
        if session not in published:
            raise web.HTTPNotFound()
        return web.json_response(await snapshot(session))

    async def artifact(request):
        session = request.match_info['session']
        filename = request.match_info['filename']
        if session not in published or filename.split('/')[-1] not in DOWNLOAD_FILES:
            raise web.HTTPNotFound()
        try:
            path = planning_view.artifact_path(session, request.match_info['batch'], filename)
        except ValueError:
            raise web.HTTPNotFound() from None
        if path.stat().st_size > 10 * 1024 * 1024:
            raise web.HTTPRequestEntityTooLarge(max_size=10 * 1024 * 1024, actual_size=path.stat().st_size)
        return web.FileResponse(path, headers={'Content-Disposition': f'attachment; filename="{path.name}"'})

    app = web.Application(middlewares=[boundary], client_max_size=1024)
    app.add_routes([web.get('/sequential', sequential),
                    web.get('/sequential-assets/{name:.*}', sequential_asset), web.get('/', index), web.get('/static/{name}', static),
                    web.get('/api/health', health), web.get('/api/models', models),
                    web.get('/api/planning/sessions', sessions), web.get('/api/planning', planning),
                    web.get('/api/artifacts/{session}/{batch}/{filename:.*}', artifact)])
    app.add_routes(recording.routes())
    return app


if __name__ == '__main__':
    config = Path(os.environ['DEMO_PUBLISHED_SESSIONS_FILE'])
    published = json.loads(config.read_text())
    if not isinstance(published, list):
        raise ValueError('Published sessions must be a JSON list')
    web.run_app(make_app(published), host='127.0.0.1',
                port=int(os.environ.get('PUBLIC_VIEW_PORT', '7200')), access_log=None)
