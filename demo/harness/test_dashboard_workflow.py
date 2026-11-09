"""Browser checks for the saved-artifact workflow map; never starts inference."""
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
class WorkflowBrowserTests(unittest.TestCase):
    def test_saved_map_details_and_unverified_states(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        code=('from demo.harness.stage import server; from aiohttp import web; '
              'app=server.make_app(); app.on_startup.clear(); '
              f'web.run_app(app,host="127.0.0.1",port={port},access_log=None)')
        process=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            url=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    with urllib.request.urlopen(url+'/api/precomputed',timeout=1) as r:
                        catalog=json.load(r)
                    break
                except OSError:time.sleep(.1)
            else:self.fail('Temporary dashboard did not start')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
                try:
                    page=browser.new_page(viewport={'width':1600,'height':1000})
                    page.add_init_script("localStorage.setItem('ideal-dashboard-help-seen-v1','1')")
                    errors=[];writes=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('request',lambda r:writes.append(r.url) if r.method!='GET' else None)
                    page.goto(url);page.wait_for_selector('.workflow-node')
                    for model in catalog['models']:
                        page.select_option('#model',model['id'])
                        for entry in (e for e in catalog['examples'] if e['model']==model['id']):
                            page.select_option('#query',entry['session'])
                            page.wait_for_function('(s)=>document.querySelector("#status").textContent.includes(s)',arg=entry['session'])
                            self.assertEqual(page.locator('.workflow-node').count(),7)
                            self.assertIn('Review needed',page.locator('[data-workflow-node="checks"]').inner_text())
                            self.assertIn('2 / 2 hash-verified passes',page.locator('[data-workflow-node="simulation"]').inner_text())
                            for name in ['context','biology','literature','proposal','checks','protocols','simulation']:
                                page.locator(f'[data-workflow-node="{name}"]').click()
                                self.assertTrue(page.locator('#workflow-dialog').is_visible())
                                self.assertIn(entry['session'],page.locator('#workflow-detail-meta').inner_text())
                                self.assertGreater(page.locator('.workflow-record').count(),0)
                                if name=='context':
                                    page.get_by_text('Saved result',exact=True).first.click()
                                    self.assertGreater(page.locator('#workflow-detail-body dl').count(),0)
                                if name=='protocols':
                                    href=page.get_by_role('link',name='OT-2 protocol',exact=True).first.get_attribute('href')
                                    self.assertEqual(page.request.get(url+href).status,200)
                                page.keyboard.press('Escape')
                                self.assertFalse(page.locator('#workflow-dialog').is_visible())
                    # Closing the modal must not also leave pane focus mode.
                    page.locator('#agent .panel-focus').click()
                    page.locator('[data-workflow-node="context"]').focus();page.keyboard.press('Enter')
                    page.keyboard.press('Escape')
                    self.assertEqual(page.locator('main.panel-focused').count(),1)
                    self.assertEqual(page.evaluate('document.activeElement.dataset.workflowNode'),'context')
                    page.keyboard.press('Escape')
                    self.assertEqual(page.locator('main.panel-focused').count(),0)
                    # A manifest success without a verified report must remain incomplete.
                    state=page.evaluate('''() => workflowMap({evidence:[],batches:[{
                      rules:{},batch:{compounds:[]},manifest:{runs:[{run_id:'r',simulation:{status:'passed'}}]},
                      runs:[{run_id:'r',simulation:null}]}]}).find(n=>n.id==='simulation')''')
                    self.assertEqual(state['badge'],'Incomplete')
                    self.assertEqual(state['subtitle'],'0 / 1 hash-verified passes')
                    page.set_viewport_size({'width':390,'height':844})
                    page.locator('[data-workflow-node="checks"]').click()
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                    bounds=page.locator('#workflow-dialog').bounding_box()
                    self.assertLessEqual(bounds['width'],390)
                    self.assertLessEqual(bounds['height'],844)
                    page.get_by_role('button',name='Close',exact=True).click()
                    self.assertEqual(errors,[])
                    self.assertEqual(writes,[])
                finally:browser.close()
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
