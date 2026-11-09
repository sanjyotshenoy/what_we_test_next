"""BYOK boundaries with fake model responses; never spends a provider key."""
import asyncio
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

from aiohttp import ClientSession, CookieJar
from aiohttp.test_utils import AioHTTPTestCase
from demo.harness import public_worker
from demo.harness.stage import planning_view, public_runs, public_view


class RunBoundaryTests(AioHTTPTestCase):
    async def get_application(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        override = patch.object(planning_view, 'RUNS', Path(self.temp.name))
        override.start(); self.addCleanup(override.stop)
        self.received = []
        async def fake_execute(manager, job, payload):
            self.received.append(dict(payload))
            payload.clear()
            job.update(state='running', message='Test worker')
            try:
                await asyncio.Event().wait()
            finally:
                job.update(state='stopped', message='Stopped')
        override = patch.object(public_runs.PublicRuns, 'execute', fake_execute)
        override.start(); self.addCleanup(override.stop)
        return public_view.make_app(['published'])

    async def start_run(self):
        return await self.client.post('/api/runs', json={'key': 'test-key-only', 'question': 'A test scientific question',
            'model': 'zai-org/GLM-5.3'}, headers={'X-Demo-Run': '1'})

    async def test_requires_key_and_same_origin_and_does_not_fall_back(self):
        for body in ({}, {'key': '', 'question': 'A test question', 'model': 'zai-org/GLM-5.3'}):
            r = await self.client.post('/api/runs', json=body, headers={'X-Demo-Run': '1'})
            self.assertEqual(r.status, 400)
        r = await self.client.post('/api/runs', json={'key': 'test-key-only'})
        self.assertEqual(r.status, 403)
        r = await self.client.post('/api/runs', json={}, headers={'X-Demo-Run': '1', 'Origin': 'https://other.example'})
        self.assertEqual(r.status, 403)
        self.assertEqual(self.received, [])

    async def test_ownership_busy_guard_stop_and_no_secret_in_responses(self):
        r = await self.start_run()
        self.assertEqual(r.status, 202)
        self.assertTrue(r.cookies[public_runs.COOKIE]['httponly'])
        data = await r.json(); session = data['session']
        self.assertNotIn('test-key-only', json.dumps(data))
        self.assertEqual((await self.start_run()).status, 429)
        for route in (f'/api/runs/{session}', f'/api/runs/{session}?after=0', f'/api/planning?session={session}'):
            self.assertEqual((await self.client.get(route)).status, 200)
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as stranger:
                response = await stranger.get(self.client.make_url(route))
                self.assertEqual(response.status, 404)
        batch = 'a' * 16
        directory = planning_view.RUNS / session / 'batches' / batch
        directory.mkdir(parents=True)
        (directory / 'batch.json').write_text('{}')
        route = f'/api/artifacts/{session}/{batch}/batch.json'
        self.assertEqual((await self.client.get(route)).status, 200)
        async with ClientSession() as stranger:
            response = await stranger.get(self.client.make_url(route))
            self.assertEqual(response.status, 404)
            response = await stranger.post(self.client.make_url(f'/api/runs/{session}/stop'), json={}, headers={'X-Demo-Run': '1'})
            self.assertEqual(response.status, 404)
        response = await self.client.get('/api/planning/sessions')
        self.assertEqual([s['session'] for s in await response.json()], ['published'])
        response = await self.client.post(f'/api/runs/{session}/stop', json={}, headers={'X-Demo-Run': '1'})
        self.assertEqual((await response.json())['state'], 'stopped')
        self.assertEqual(self.received[0]['key'], 'test-key-only')

    async def test_public_dashboard_assets_and_old_sequential(self):
        for url in ('/', '/planner', '/results', '/static/dashboard-workflow.js', '/static/vendor/cytoscape.min.js',
                    '/static/vendor/smiles-drawer-2.0.0.min.js', '/static/data/molecules/CHEMBL8.svg', '/sequential'):
            response = await self.client.get(url)
            self.assertEqual(response.status, 200, url)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        response = await self.client.get('/')
        html = await response.text()
        self.assertIn('Agent workflow', html)
        self.assertRegex(html, r'dashboard-workflow.js\?v=[0-9a-f]{16}')
        response = await self.client.get('/api/precomputed')
        self.assertEqual((await response.json())['examples'], [])


class WorkerTests(unittest.TestCase):
    def test_environment_cannot_inherit_provider_credentials(self):
        with patch.dict('os.environ', {'NEBIUS_API_KEY': 'never-inherit', 'OPENAI_API_KEY': 'never-inherit',
                                     'OPENCODE_CONFIG': '/private', 'NEBIUS_BASE_URL': 'https://evil.example'}):
            env = public_runs.worker_environment()
        self.assertFalse(set(env) & {'NEBIUS_API_KEY', 'OPENAI_API_KEY', 'NEBIUS_BASE_URL', 'OPENCODE_CONFIG'})
        self.assertEqual(env['PYTHON_DOTENV_DISABLED'], '1')

    def test_bounded_real_tool_dispatch_and_simulation_completion(self):
        chat = Mock(side_effect=[json.dumps({'tool': 'planning_context', 'args': {}}),
                                 json.dumps({'tool': 'planning_simulate', 'args': {'batch_id': 'a'*16}})])
        with patch.object(public_worker, 'tool', side_effect=[{'submission_schema': {}}, {'status': 'simulated'}]) as tool, \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            public_worker.run({'question': 'Test question', 'model': 'test-model'}, chat, 'test-session')
        self.assertEqual(tool.call_count, 2)
        self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['state'], 'finished')
        self.assertEqual(chat.call_args.kwargs['timeout'], 120)

    def test_invalid_actions_stop_and_no_key_fallback(self):
        for response in ('not JSON', '{"tool":"bash","args":{"cmd":"bad"}}'):
            with patch.object(public_worker, 'tool') as tool, patch('sys.stdout', new_callable=io.StringIO) as out:
                public_worker.run({'question': 'Test question', 'model': 'test'}, Mock(return_value=response), 'test-session')
            tool.assert_not_called()
            self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['state'], 'failed')
        with patch('sys.stdin', io.StringIO('{"key":""}\n')), patch.dict('os.environ', {'NEBIUS_API_KEY': 'saved-key'}):
            with self.assertRaises(ValueError): public_worker.main()

    def test_real_tool_adapter_preserves_progress_and_rejection(self):
        import shutil
        import uuid
        session='test_live_'+uuid.uuid4().hex
        try:
            with patch('sys.stdout',new_callable=io.StringIO) as out:
                result=public_worker.tool('planning_submit',{'batch':{}},session)
            self.assertEqual(result['status'],'rejected')
            events=[json.loads(line) for line in out.getvalue().splitlines()]
            self.assertIn('checks',[event.get('stage') for event in events])
        finally:
            shutil.rmtree(planning_view.session_path(session),ignore_errors=True)

    def test_turn_limit(self):
        chat = Mock(return_value='{"tool":"planning_context","args":{}}')
        with patch.object(public_worker, 'tool', return_value={'error': 'budget exhausted'}), patch('sys.stdout', new_callable=io.StringIO):
            public_worker.run({'question': 'Test question', 'model': 'test'}, chat, 'test-session')
        self.assertEqual(chat.call_count, 16)


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_key_pipe_and_worker_exit(self):
        import sys
        original = asyncio.create_subprocess_exec
        calls = []
        # Exercise the real worker entry point with an in-process fake provider.
        # Neither provider network access nor the six production tools are invoked.
        code = '''import sys, types, os
from demo.harness import public_worker
client=types.SimpleNamespace(max_retries=2,chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: None)))
def get_client():
    assert os.environ['NEBIUS_API_KEY']=='pipe-test-key'
    return client
def chat(*args, **kwargs):
    assert 'NEBIUS_API_KEY' not in os.environ
    return '{"done":true}'
sys.modules['wwtn.llm']=types.SimpleNamespace(client=get_client,chat=chat)
public_worker.main()
'''
        async def spawn(*args, **kwargs):
            calls.append((args, kwargs['env']))
            return await original(sys.executable, '-c', code, 'test-session', **kwargs)
        payload = dict(key='pipe-test-key',question='A test question',model='test-model')
        job = dict(session='test-session',state='starting',message='')
        with patch.object(asyncio, 'create_subprocess_exec', spawn):
            await public_runs.PublicRuns().execute(job, payload)
        self.assertEqual(job['state'], 'finished')
        self.assertEqual(payload, {})
        self.assertNotIn('pipe-test-key', repr(calls))
        self.assertNotIn('pipe-test-key', repr(job))

    async def test_cancel_terminates_worker(self):
        import sys
        original = asyncio.create_subprocess_exec
        processes = []
        ready = asyncio.Event()
        async def spawn(*args, **kwargs):
            process = await original(sys.executable, '-c', 'import sys,time; sys.stdin.readline(); time.sleep(60)', **kwargs)
            processes.append(process); ready.set()
            return process
        job = dict(session='test-session',state='starting',message='')
        with patch.object(asyncio, 'create_subprocess_exec', spawn):
            task = asyncio.create_task(public_runs.PublicRuns().execute(job, dict(key='test-key')))
            await ready.wait()
            await asyncio.sleep(.05)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(job['state'], 'stopped')
        self.assertIsNotNone(processes[0].returncode)


class VisibleStreamingTests(unittest.TestCase):
    def test_visible_content_streams_but_reasoning_is_excluded(self):
        from types import SimpleNamespace as NS
        from demo.harness.visible_stream import completion_bridge
        class Stream:
            closed = False
            def __iter__(self):
                yield NS(choices=[NS(delta=NS(content=None, reasoning_content='PRIVATE-REASONING'),finish_reason=None)])
                yield NS(choices=[NS(delta=NS(content='a'*260, reasoning_content='PRIVATE-REASONING'),finish_reason=None)])
                # First output is published before the stream reaches its end.
                self_test.assertEqual(parts,['a'*260])
                yield NS(choices=[NS(delta=NS(content='done'),finish_reason='stop')])
            def close(self): self.closed=True
        self_test=self;parts=[];stream=Stream();create=Mock(return_value=stream)
        result=completion_bridge(create,parts.append)(model='test')
        self.assertEqual(result.choices[0].message.content,'a'*260+'done')
        self.assertNotIn('PRIVATE-REASONING',''.join(parts))
        self.assertTrue(stream.closed)
        self.assertTrue(create.call_args.kwargs['stream'])

    def test_provider_reasoning_is_separate_and_does_not_change_completion(self):
        from types import SimpleNamespace as NS
        from demo.harness.visible_stream import completion_bridge
        class Stream:
            def __iter__(self):
                yield NS(choices=[NS(delta=NS(content=None,model_extra={'reasoning_content':'Test provider reasoning','api_key':'DO-NOT-FORWARD'}),finish_reason=None)])
                yield NS(choices=[NS(delta=NS(content='{"done":true}',model_extra={}),finish_reason='stop')])
            def close(self):pass
        output=[];reasoning=[]
        result=completion_bridge(Mock(return_value=Stream()),output.append,reasoning.append)()
        self.assertEqual(reasoning,['Test provider reasoning'])
        self.assertEqual(''.join(output),'{"done":true}')
        self.assertEqual(result.choices[0].message.content,'{"done":true}')
        self.assertNotIn('DO-NOT-FORWARD',''.join(output+reasoning))

    def test_truncated_stream_is_not_accepted_as_a_complete_action(self):
        from types import SimpleNamespace as NS
        from demo.harness.visible_stream import completion_bridge
        stream=Mock()
        stream.__iter__=Mock(return_value=iter([NS(choices=[NS(delta=NS(content='{"done":true}'),finish_reason='length')])]))
        with self.assertRaises(ValueError): completion_bridge(Mock(return_value=stream),lambda text:None)()
        stream.close.assert_called_once()

    def test_event_cursor_bounds_and_allowlisted_fields(self):
        manager=public_runs.PublicRuns()
        job=dict(session='test',state='running',message='',model='model',question='question')
        manager.record(job,dict(state='running',message='Generating',kind='model_start',stage='model',turn=1))
        manager.record(job,dict(state='running',message='Visible text',kind='model_delta',stage='model',text='{}',
                                reasoning_content='PRIVATE-REASONING',api_key='PRIVATE-KEY'))
        public=manager.public(job,after=1)
        self.assertEqual([e['id'] for e in public['events']],[2])
        self.assertNotIn('PRIVATE',json.dumps(public))
        self.assertNotIn('events',manager.public(job))
        for _ in range(2100):manager.record(job,dict(state='running',message='Text',kind='model_delta',text='chunk'))
        self.assertEqual(len(job['events']),2000)
        self.assertTrue(manager.public(job,after=0)['events_truncated'])
