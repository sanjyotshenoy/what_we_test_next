import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from aiohttp.test_utils import AioHTTPTestCase
from demo.harness import budget, planning_pipeline as pipeline
from demo.harness.test_planning_pipeline import fixture_batch, seed_context
from demo.harness.stage import planning_view as view, server


class ArtifactTests(AioHTTPTestCase):
    async def get_application(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        for module in (pipeline, view):
            p = patch.object(module, 'RUNS', Path(self.temp.name)); p.start(); self.addCleanup(p.stop)
        p = patch.object(server, 'REPLAY', True); p.start(); self.addCleanup(p.stop)
        seed_context('fixture')
        result = pipeline.submit(fixture_batch(1, 1), 'fixture')
        self.batch = result['batch_id']
        self.directory = Path(result['manifest']).parent
        return server.make_app()

    async def test_session_isolation_and_download_boundaries(self):
        response = await self.client.get('/api/planning?session=other')
        self.assertEqual((await response.json())['batches'], [])
        response = await self.client.get('/api/planning?session=../fixture')
        self.assertEqual(response.status, 400)
        for name, status in [('run-001/protocol.py', 200), ('private.json', 404)]:
            response = await self.client.get(f'/api/artifacts/fixture/{self.batch}/{name}')
            self.assertEqual(response.status, status)
        private = Path(self.temp.name) / 'private.json'; private.write_text('{"secret":"fixture"}')
        target = self.directory / 'batch.json'; target.unlink(); target.symlink_to(private)
        data = view.snapshot('fixture')
        self.assertIsNone(data['batches'][0]['batch'])
        response = await self.client.post('/api/prompt', json={'text':'test'})
        self.assertEqual(response.status, 409)

    async def test_stale_and_corrupt_artifacts_do_not_pass(self):
        manifest = json.loads((self.directory/'manifest.json').read_text())
        manifest['runs'][0]['simulation'] = {'status':'passed'}
        pipeline.save(self.directory/'manifest.json', manifest)
        data = view.snapshot('fixture')
        self.assertEqual(data['batches'][0]['manifest']['runs'][0]['simulation']['status'], 'stale')
        for content in ['{', '[]', 'null']:
            (self.directory/'manifest.json').write_text(content)
            self.assertEqual(view.snapshot('fixture')['batches'], [])
            self.assertEqual(view.sessions(), [])


class BudgetTests(unittest.TestCase):
    def test_failed_attempts_cannot_bypass_correction_limit(self):
        with TemporaryDirectory() as d, patch.object(budget, 'RUNS', Path(d)):
            for _ in range(3): budget.consume('planning_submit', 'session')
            with self.assertRaises(ValueError): budget.consume('planning_submit', 'session')
            budget.consume('planning_submit', 'other')
            with self.assertRaises(ValueError): budget.consume('planning_submit', '../escape')
