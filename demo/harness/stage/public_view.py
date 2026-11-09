"""Public saved dashboard and isolated, visitor-key-only planning runs."""
import asyncio
from collections import deque
import json
import os
from pathlib import Path
import time

from aiohttp import web
from demo.harness.stage import planning_view, recording
from demo.harness.stage.assets import versioned_html
from demo.harness.stage.public_runs import PublicRuns
from demo.harness.stage.visitors import VisitorRequests

STATIC = Path(__file__).parent / 'static'
DEMO_STATIC = Path(__file__).resolve().parents[2]
SEQUENTIAL_FILES = {'sequential-models.json', 'demo.css', 'sequential.css', 'sequential.js',
                    'fonts/Lato-Regular.woff2', 'fonts/Lato-Semibold.woff2', 'fonts/Lato-Bold.woff2'}
STATIC_FILES = {'visitor-session.js', 'planner.css', 'planner.js', 'app.css', 'saved-dashboard.css', 'saved-dashboard.js',
                'dashboard-visuals.js', 'dashboard-layout.js', 'dashboard-workflow.js', 'dashboard-workflow.css',
                'public-planner.js', 'public-planner.css', 'vendor/cytoscape.min.js',
                'vendor/smiles-drawer-2.0.0.min.js', 'data/molecules/provenance.json'}
STATIC_FILES |= {f'data/molecules/{compound}.{suffix}' for compound in ('CHEMBL8', 'CHEMBL454950')
                 for suffix in ('svg', 'mol')}
DOWNLOAD_FILES = planning_view.BATCH_FILES | (planning_view.RUN_FILES - {'simulator.log'})


def make_app(published, *, request_limit=600, visitor_requests=None):
    published = tuple(published)
    if not published or any(not planning_view.TOKEN.fullmatch(s) for s in published):
        raise ValueError('Explicit published session IDs are required')
    live = PublicRuns()
    requests = deque()
    visitor_requests = visitor_requests or VisitorRequests()
    cache = {}
    lock = asyncio.Lock()

    @web.middleware
    async def boundary(request, handler):
        now = time.monotonic()
        bucket = request.get('visitor_requests', requests)
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= request_limit and not request.path.startswith('/static/') and not request.path.endswith('/stop'):
            return web.Response(status=429, text='Please wait before refreshing.', headers={'Retry-After': '60'})
        if not request.path.startswith('/static/'):
            bucket.append(now)
        if request.method not in {'GET', 'HEAD'}:
            if request.method != 'POST' or not (request.path == '/api/runs' or
                    request.path.startswith('/api/runs/') and request.path.endswith('/stop')):
                return web.Response(status=405, text='This endpoint is read-only.')
            if request.headers.get('X-Demo-Run') != '1' or request.content_type != 'application/json':
                return web.Response(status=403, text='Use the live planning form.')
            origin = request.headers.get('Origin')
            if origin and origin not in (f'https://{request.host}', f'http://{request.host}'):
                return web.Response(status=403, text='Cross-site requests are not allowed.')
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = web.Response(status=exc.status, text=exc.text)
        except Exception:
            response = web.Response(status=503, text='Results temporarily unavailable.')
        response.headers.update({
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        })
        return response

    async def index(request):
        name = 'public-planner.html' if request.path == '/planner' else ('planner.html' if request.path == '/results' else 'saved-dashboard.html')
        html = await asyncio.to_thread(versioned_html, name)
        if name == 'saved-dashboard.html':
            html = html.replace('<a href="/planner">Live planning</a>', '<a href="/sequential">Walkthrough</a><a href="/planner">Live planning</a>')
        return web.Response(text=html, content_type='text/html')

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

    async def visitor(request):
        return web.json_response({'admitted': True})

    async def health(request):
        return web.json_response({'ok': True, 'opencode': False, 'replay': True,
                                  'read_only': True, 'byok_runs': True, 'default_session': published[0]})

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
        if session not in published:
            return await asyncio.to_thread(planning_view.snapshot, session)
        async with lock:
            now = time.monotonic()
            if session not in cache or now - cache[session][0] > 2:
                data = await asyncio.to_thread(planning_view.snapshot, session)
                cache[session] = (now, data)
            return cache[session][1]

    async def planning(request):
        session = request.query.get('session', published[0])
        if session not in published and not live.visible(request, session):
            raise web.HTTPNotFound()
        return web.json_response(await snapshot(session))

    async def artifact(request):
        session = request.match_info['session']
        filename = request.match_info['filename']
        if (session not in published and not live.visible(request, session)) or filename.split('/')[-1] not in DOWNLOAD_FILES:
            raise web.HTTPNotFound()
        try:
            path = planning_view.artifact_path(session, request.match_info['batch'], filename)
        except ValueError:
            raise web.HTTPNotFound() from None
        if path.stat().st_size > 10 * 1024 * 1024:
            raise web.HTTPRequestEntityTooLarge(max_size=10 * 1024 * 1024, actual_size=path.stat().st_size)
        return web.FileResponse(path, headers={'Content-Disposition': f'attachment; filename="{path.name}"'})

    async def precomputed(request):
        catalog = json.loads((DEMO_STATIC / 'sequential-models.json').read_text())
        examples = []
        for session, model in catalog['sessions'].items():
            if session not in published:
                continue
            data = await snapshot(session)
            runs = [r for b in data['batches'] for r in b['manifest']['runs']]
            if runs:
                compounds = list(dict.fromkeys(r['compound'] for r in runs))
                species = list(dict.fromkeys(r['species']['name'] for r in runs))
                examples.append(dict(session=session, model=model, question=' / '.join(compounds) + ' · ' + ' / '.join(species)))
        queries = []
        for name in ('ciprofloxacin-panel', 'antibiotic-comparison'):
            prompt = (DEMO_STATIC / 'examples' / f'{name}.txt').read_text()
            label = prompt.splitlines()[0].removeprefix('Scientist question: ').split('?')[0] + '?'
            queries.append(dict(id=name, label=label, prompt=prompt))
        return web.json_response(dict(models=catalog['models'], examples=examples, queries=queries))

    async def graph(request):
        from demo.harness.dashboard_graph import overview
        return web.json_response(await asyncio.to_thread(overview))

    app = web.Application(middlewares=[visitor_requests.middleware, boundary], client_max_size=20000)
    app.cleanup_ctx.append(live.lifecycle)
    app.add_routes([web.get('/results', index), web.get('/planner', index),
                    web.get('/api/precomputed', precomputed), web.get('/api/graph/overview', graph),
                    web.post('/api/runs', live.start), web.get('/api/runs/{session}', live.get),
                    web.post('/api/runs/{session}/stop', live.stop)])
    app.add_routes([web.get('/sequential', sequential),
                    web.get('/sequential-assets/{name:.*}', sequential_asset), web.get('/', index), web.get('/static/{name:.*}', static),
                    web.get('/api/health', health), web.get('/api/visitor', visitor), web.get('/api/models', models),
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
