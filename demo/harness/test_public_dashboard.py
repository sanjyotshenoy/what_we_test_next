"""Public dashboard CSP and BYOK form browser checks without inference."""
import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from playwright.sync_api import sync_playwright
from demo.harness.paths import DEMO, ROOT


@unittest.skipUnless((DEMO/'harness/planning_runs/ses_e43f7ded3ffewajMKYz0MUSIt5').is_dir(),
                     'Requires local saved demo trajectories')
class PublicDashboardBrowserTests(unittest.TestCase):
    def test_graph_molecule_walkthrough_and_key_form(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port=sock.getsockname()[1]
        code=('from demo.harness.stage.public_view import make_app; from aiohttp import web; '
              'app=make_app(["ses_e43f7ded3ffewajMKYz0MUSIt5"]); '
              f'web.run_app(app,host="127.0.0.1",port={port},access_log=None)')
        process=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            url=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(url+'/api/health',timeout=1).close();break
                except OSError:time.sleep(.1)
            else:self.fail('Temporary public dashboard did not start')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
                try:
                    page=browser.new_page(viewport={'width':1600,'height':1000})
                    errors=[]; failures=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('response',lambda r:failures.append((r.status,r.url)) if r.status>=400 else None)
                    page.goto(url);page.wait_for_selector('.workflow-node')
                    self.assertEqual(page.locator('.workflow-node').count(),7)
                    self.assertEqual(page.locator('.well').count(),96)
                    page.locator('[data-workflow-node="proposal"]').click()
                    self.assertTrue(page.locator('#workflow-dialog').is_visible())
                    page.keyboard.press('Escape')
                    for _ in range(50):
                        if page.evaluate('graph && graph.nodes().length > 500'):break
                        page.wait_for_timeout(100)
                    page.evaluate("()=>{graph.getElementById('CHEMBL8').emit('tap');}")
                    page.wait_for_selector('#molecules svg')
                    page.locator('#kg .panel-focus').click()
                    page.keyboard.press('Escape')
                    self.assertEqual(errors,[])
                    self.assertEqual(failures,[])
                    page.goto(url+'/sequential')
                    self.assertIn('scientific question',page.locator('body').inner_text().lower())
                    page.goto(url+'/planner')
                    page.wait_for_selector('#live-model option',state='attached')
                    self.assertEqual(page.locator('#live-key').input_value(),'')
                    self.assertEqual(page.locator('#live-example option').count(),2)
                    for query in ('ciprofloxacin-panel','antibiotic-comparison'):
                        page.select_option('#live-example',query)
                        self.assertEqual(page.locator('#live-question').input_value(),(DEMO/'examples'/f'{query}.txt').read_text())
                    self.assertEqual(page.locator('#live-key').input_value(),'')
                    page.fill('#live-key','test-key-never-real')
                    sent=[]
                    def fake_start(route):
                        sent.append(route.request.post_data_json)
                        route.fulfill(status=202,content_type='application/json',body=json.dumps(dict(
                            session='public_test',state='finished',message='Browser test only',model='test',question='test')))
                    page.route('**/api/runs',fake_start)
                    page.route('**/api/runs/public_test*',lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps(dict(
                            session='public_test',state='finished',message='Browser test only',model='test',question='test'))))
                    page.route('**/api/planning?session=public_test',lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps(dict(session='public_test',evidence=[],batches=[]))))
                    page.click('#start');page.wait_for_url('**/?run=public_test')
                    page.wait_for_selector('#live-toolbar:visible')
                    self.assertEqual(sent[0]['question'],(DEMO/'examples/antibiotic-comparison.txt').read_text())
                    self.assertEqual(sent[0]['key'],'test-key-never-real')
                    self.assertEqual(page.locator('#live-key').count(),0)
                    storage=page.evaluate('JSON.stringify({local:localStorage,session:sessionStorage})')
                    self.assertNotIn('test-key-never-real',storage)
                    self.assertNotIn('test-key-never-real',page.url)
                    self.assertEqual(errors,[])
                finally:browser.close()
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
