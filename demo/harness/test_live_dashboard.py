"""Live dashboard progression with synthetic events and real saved artifacts.

Test-only responses never invoke a provider or manufacture production artifacts.
"""
import copy
import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright, expect
from demo.harness.paths import DEMO, ROOT
from demo.harness.stage import planning_view

SAVED='ses_e43f7ded3ffewajMKYz0MUSIt5'


@unittest.skipUnless((DEMO/'harness/planning_runs'/SAVED).is_dir(),'Requires local saved trajectories')
class LiveDashboardBrowserTests(unittest.TestCase):
    def test_live_stages_outputs_artifacts_and_preserved_interaction(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        code=('from demo.harness.stage.public_view import make_app; from aiohttp import web; '
              f'web.run_app(make_app(["{SAVED}"]),host="127.0.0.1",port={port},access_log=None)')
        process=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            base=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:urllib.request.urlopen(base+'/api/health',timeout=1).close();break
                except OSError:time.sleep(.1)
            session='public_ui_test'
            saved=planning_view.snapshot(SAVED);saved['session']=session
            state={'job':dict(session=session,state='running',message='Generating',model='test',question=(DEMO/'examples/ciprofloxacin-panel.txt').read_text(),stage='model',turn=1,steps={}),
                   'snapshot':dict(session=session,evidence=[],batches=[]),'events':[]}
            def event(kind,text='',stage='model',**kwargs):
                state['events'].append(dict(id=len(state['events'])+1,kind=kind,text=text,stage=stage,message=kind,turn=1,elapsed=1,**kwargs))
            event('model_start');event('model_delta','{"tool": "planning_context",')
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
                try:
                    page=browser.new_page(viewport={'width':1600,'height':1000})
                    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                    def job(route):
                        after=int(urllib.parse.parse_qs(urllib.parse.urlparse(route.request.url).query).get('after',['0'])[0])
                        route.fulfill(content_type='application/json',body=json.dumps({**state['job'],'events':[e for e in state['events'] if e['id']>after]}))
                    page.route('**/api/runs/public_ui_test*',job)
                    page.route('**/api/planning?session=public_ui_test',lambda r:r.fulfill(content_type='application/json',body=json.dumps(state['snapshot'])))
                    page.goto(base+'/?run='+session)
                    expect(page.locator('.workflow-node')).to_have_count(8)
                    expect(page.locator('[data-workflow-node="model"]')).to_have_class('workflow-node running')
                    page.locator('[data-workflow-node="model"]').click()
                    expect(page.locator('#workflow-model-output')).to_contain_text('planning_context')
                    event('model_delta',' "args": {}} <script>window.injected=true</script>')
                    expect(page.locator('#workflow-model-output')).to_contain_text('window.injected')
                    self.assertIsNone(page.evaluate('window.injected'))
                    self.assertTrue(page.locator('#workflow-dialog').is_visible())
                    page.keyboard.press('Escape')
                    # Keep a graph-selected molecule and graph zoom while artifacts accumulate.
                    for _ in range(50):
                        if page.evaluate('graph && graph.nodes().length > 500'):break
                        page.wait_for_timeout(100)
                    page.evaluate("()=>{graph.zoom(.3);graph.getElementById('CHEMBL8').emit('tap');}")
                    page.wait_for_selector('#molecules svg')
                    for stage in ('context','biology','literature','checks','protocols','simulation'):
                        state['job'].update(stage=stage,message=f'Running {stage}')
                        state['snapshot']['evidence']=saved['evidence']
                        if stage in ('protocols','simulation'):
                            state['snapshot']['batches']=copy.deepcopy(saved['batches'])
                            for batch in state['snapshot']['batches']:
                                for run in batch['manifest']['runs']:run['simulation']={'status':'not_run'}
                                for run in batch['runs']:run['simulation']=None
                        event('tool_start','{"draft":true}',stage=stage,tool='planning_submit' if stage=='checks' else stage)
                        expect(page.locator(f'[data-workflow-node="{stage}"]')).to_have_class('workflow-node running',timeout=5000)
                        self.assertEqual(page.locator('.workflow-node.running').count(),1)
                        self.assertAlmostEqual(page.evaluate('graph.zoom()'),.3)
                        self.assertIn('CHEMBL8',page.locator('#molecule-selection').inner_text())
                        if stage=='checks':
                            page.locator('[data-workflow-node="proposal"]').click()
                            expect(page.locator('#workflow-detail-body')).to_contain_text('draft')
                            page.keyboard.press('Escape')
                        if stage=='protocols':expect(page.locator('.well')).to_have_count(96)
                    page.locator('#live-output-tab').click()
                    expect(page.locator('#live-output-events')).to_contain_text('planning_context')
                    self.assertIsNone(page.evaluate('window.injected'))
                    state['job'].update(state='finished',message='Simulation finished')
                    state['snapshot']=saved
                    page.locator('#live-workflow-tab').click()
                    expect(page.locator('#run-tag')).to_have_text('finished',timeout=5000)
                    expect(page.locator('.workflow-node.running')).to_have_count(0)
                    expect(page.locator('[data-workflow-node="simulation"]')).to_contain_text('2 / 2 hash-verified passes')
                    expect(page.locator('#live-stop')).to_be_disabled()
                    self.assertEqual(errors,[])
                    page.set_viewport_size({'width':390,'height':844})
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                finally:browser.close()
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
