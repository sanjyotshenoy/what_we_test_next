"""Public boundary tests: no agent, credentials, writes or unpublished artifacts."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from aiohttp.test_utils import AioHTTPTestCase
from demo.harness.stage import public_view, planning_view


class PublicViewTests(AioHTTPTestCase):
    async def get_application(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        override = patch.object(planning_view, 'RUNS', self.root)
        override.start(); self.addCleanup(override.stop)
        self.batch = 'a' * 16
        for session in ('published', 'private'):
            directory = self.root / session / 'batches' / self.batch
            directory.mkdir(parents=True)
            (directory / 'manifest.json').write_text(json.dumps({'batch_id': self.batch, 'runs': []}))
            (directory / 'run-001').mkdir()
            (directory / 'run-001/protocol.py').write_text('# reference\n')
            (directory / 'run-001/simulator.log').write_text('private diagnostic')
        return public_view.make_app(['published'])

    async def test_only_explicitly_published_sessions_are_visible(self):
        response = await self.client.get('/api/planning/sessions')
        self.assertEqual([s['session'] for s in await response.json()], ['published'])
        for session in ('private', '../private', ''):
            response = await self.client.get('/api/planning', params={'session': session})
            self.assertEqual(response.status, 404)
        response = await self.client.get('/api/planning')
        self.assertEqual((await response.json())['session'], 'published')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')

    async def test_controls_transcripts_and_private_files_are_unreachable(self):
        for route in ('/api/keys', '/api/transcript', '/api/stream', '/api/activity',
                      '/legacy', '/static/data/rehearsal.txt', '/static/../server.py'):
            response = await self.client.get(route)
            self.assertEqual(response.status, 404, route)
        for route in ('/api/prompt', '/api/new', '/api/abort', '/api/keys', '/api/panel'):
            response = await self.client.post(route, json={'text': 'must not reach an agent'})
            self.assertEqual(response.status, 405, route)

    async def test_downloads_cannot_escape_published_artifacts(self):
        base = f'/api/artifacts/published/{self.batch}/'
        response = await self.client.get(base + 'run-001/protocol.py')
        self.assertEqual(response.status, 200)
        self.assertIn('attachment', response.headers['Content-Disposition'])
        for route in (base + 'run-001/simulator.log',
                      f'/api/artifacts/private/{self.batch}/manifest.json'):
            response = await self.client.get(route)
            self.assertEqual(response.status, 404)
        path = self.root / 'published' / 'batches' / self.batch / 'batch.json'
        path.symlink_to(self.root / 'private' / 'batches' / self.batch / 'manifest.json')
        response = await self.client.get(base + 'batch.json')
        self.assertEqual(response.status, 404)

    async def test_sequential_assets_are_explicit_and_read_only(self):
        for route in ('/sequential', '/sequential-assets/sequential.js',
                      '/sequential-assets/sequential.css', '/sequential-assets/demo.css',
                      '/sequential-assets/fonts/Lato-Regular.woff2'):
            self.assertEqual((await self.client.get(route)).status, 200, route)
        for route in ('/sequential-assets/.env', '/sequential-assets/private/published_sessions.json',
                      '/sequential-assets/harness/stage/server.py'):
            self.assertEqual((await self.client.get(route)).status, 404, route)
        self.assertEqual((await self.client.post('/sequential')).status, 405)

    async def test_missing_allowlist_fails_closed(self):
        for sessions in ([], ['../escape']):
            with self.assertRaises(ValueError):
                public_view.make_app(sessions)


class RateLimitTests(AioHTTPTestCase):
    async def get_application(self):
        return public_view.make_app(['published'], request_limit=2)

    async def test_requests_are_bounded(self):
        for _ in range(2):
            self.assertEqual((await self.client.get('/api/health')).status, 200)
        response = await self.client.get('/api/health')
        self.assertEqual(response.status, 429)
        self.assertEqual(response.headers['Retry-After'], '60')


class VisitorAdmissionTests(AioHTTPTestCase):
    async def get_application(self):
        from demo.harness.stage.visitors import Visitors
        self.now = 1000
        self.visitors = Visitors(clock=lambda: self.now)
        return public_view.make_app(['published'], visitors=self.visitors)

    async def test_thirty_browsers_then_busy_and_expiry(self):
        tokens = []
        for _ in range(30):
            self.client.session.cookie_jar.clear()
            response = await self.client.get('/')
            self.assertEqual(response.status, 200)
            self.assertIn('/static/visitor-session.js', await response.text())
            tokens.append(response.cookies['demo_visitor'].value)
        self.client.session.cookie_jar.clear()
        response = await self.client.get('/')
        self.assertEqual(response.status, 429)
        self.assertEqual(response.headers['Retry-After'], '15')
        self.assertIn('retry automatically', await response.text())
        self.assertNotIn('demo_visitor', response.cookies)
        self.assertEqual((await self.client.get('/api/visitor')).status, 429)
        self.assertEqual((await self.client.get('/api/health')).status, 200)
        self.assertEqual((await self.client.get('/sequential')).status, 429)
        self.assertEqual((await self.client.get('/static/visitor-session.js')).status, 200)
        # An admitted browser's other tabs and navigation reuse the same slot.
        self.now += 90
        self.client.session.cookie_jar.update_cookies({'demo_visitor': tokens[0]})
        response = await self.client.get('/api/visitor')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.cookies['demo_visitor'].value, tokens[0])
        self.assertEqual(len(self.visitors.sessions), 30)
        self.now += 31
        self.client.session.cookie_jar.clear()
        self.assertEqual((await self.client.get('/')).status, 200)
        self.assertEqual(len(self.visitors.sessions), 2)
        self.assertIn(tokens[0], self.visitors.sessions)

    async def test_simultaneous_arrivals_do_not_overbook(self):
        import asyncio
        from aiohttp import ClientSession, DummyCookieJar
        async with ClientSession(cookie_jar=DummyCookieJar()) as clients:
            async def arrive():
                async with clients.get(self.server.make_url('/api/visitor')) as response:
                    await response.read()
                    return response.status
            statuses = await asyncio.gather(*(arrive() for _ in range(100)))
        self.assertEqual(statuses.count(200), 30)
        self.assertEqual(statuses.count(429), 70)
        self.assertEqual(len(self.visitors.sessions), 30)

    async def test_full_gate_does_not_block_owned_stop_route(self):
        self.visitors.limit = 1
        self.assertEqual((await self.client.get('/')).status, 200)
        self.client.session.cookie_jar.clear()
        response = await self.client.post('/api/runs/unknown/stop', json={}, headers={'X-Demo-Run': '1'})
        self.assertEqual(response.status, 404)  # Ownership handler, not admission rejection.
        self.assertEqual((await self.client.get('/planner')).status, 429)
        self.assertEqual((await self.client.get('/results')).status, 429)


class VisitorRateTests(AioHTTPTestCase):
    async def get_application(self):
        return public_view.make_app(['published'], request_limit=2)

    async def test_each_visitor_has_a_separate_budget(self):
        for _ in range(2):
            self.assertEqual((await self.client.get('/api/visitor')).status, 200)
        self.assertEqual((await self.client.get('/api/visitor')).status, 429)
        self.assertEqual((await self.client.get('/static/visitor-session.js')).status, 200)
        self.client.session.cookie_jar.clear()
        self.assertEqual((await self.client.get('/api/visitor')).status, 200)
