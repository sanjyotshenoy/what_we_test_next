"""Local-artifact browser regression for dashboard resizing, focus and graph selection.

No inference: temporary server startup hooks are disabled. Skips on source-only clones.
"""
import socket,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
import unittest
from demo.harness.paths import DEMO

@unittest.skipUnless((DEMO / "harness/planning_runs/ses_e43f7ded3ffewajMKYz0MUSIt5").is_dir(), "Requires saved demo trajectories")
class DashboardLayoutTests(unittest.TestCase):
    def test_layout_and_graph_molecule_selection(self):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        code=f'from demo.harness.stage import server; from aiohttp import web; app=server.make_app(); app.on_startup.clear(); web.run_app(app,host="127.0.0.1",port={port},access_log=None)'
        p=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
         url=f'http://127.0.0.1:{port}'
         for _ in range(100):
          try:urllib.request.urlopen(url+'/api/precomputed',timeout=1);break
          except OSError:time.sleep(.1)
         with sync_playwright() as pw:
          browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1600,'height':1000});errors=[];writes=[];external=[]
          page.on('pageerror',lambda e:errors.append(str(e)))
          page.on('request',lambda r:writes.append(r.url) if r.method!='GET' else None)
          page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url) else None)
          page.add_init_script("localStorage.setItem('ideal-dashboard-help-seen-v1','1')")
          page.goto(url);page.wait_for_function('graph && graph.nodes().length===605')
          boxes={name:page.locator('#'+name).bounding_box() for name in ['kg','structure','plate','video','robot']}
          assert abs(boxes['kg']['x']-boxes['structure']['x'])<1
          assert boxes['structure']['y']>boxes['kg']['y']+boxes['kg']['height']
          assert boxes['plate']['x']>boxes['kg']['x']+boxes['kg']['width']
          assert abs(boxes['plate']['x']-boxes['video']['x'])<1
          assert abs(boxes['plate']['x']-boxes['robot']['x'])<1
          assert boxes['plate']['y']<boxes['video']['y']<boxes['robot']['y']
          def width():return page.locator('#agent').bounding_box()['width']
          before=width();h=page.locator('.pane-divider.columns').first.bounding_box();x=h['x']+5;y=h['y']+50
          page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+90,y,steps=10);page.mouse.up();page.wait_for_timeout(150)
          assert width()>before+50,(width(),before)
          changed=width();page.reload();page.wait_for_function('graph && graph.nodes().length===605');assert abs(width()-changed)<2
          row=page.locator('.pane-divider.rows').first;box=row.bounding_box();before_height=page.locator('#plate').bounding_box()['height']
          page.mouse.move(box['x']+50,box['y']+5);page.mouse.down();page.mouse.move(box['x']+50,box['y']+55,steps=10);page.mouse.up();page.wait_for_timeout(150)
          assert page.locator('#plate').bounding_box()['height']>before_height+30
          page.locator('.pane-divider.columns').first.focus();w=width();page.keyboard.press('ArrowRight');page.wait_for_timeout(100);assert width()>w
          # Focus/restore each panel, preserving sizes and loaded content.
          before=width()
          for identity in ['agent','kg','plate','structure','video','robot']:
           page.locator('#'+identity+' .panel-focus').click();page.wait_for_timeout(100)
           assert page.locator('main.panel-focused').count()==1
           assert page.locator('main > .panel[hidden]').count()==5
           assert page.locator('#'+identity).bounding_box()['width']>1500
           page.keyboard.press('Escape');page.wait_for_timeout(100)
           assert page.locator('main.panel-focused').count()==0
          assert abs(width()-before)<2
          page.click('#header-more summary');page.click('#reset-layout');page.wait_for_timeout(100);assert abs(width()-changed)>40
          # Actual pointer click on a full-KG compound selects its SMILES/drawing.
          pos=page.evaluate("() => {const p=graph.getElementById('CHEMBL8').renderedPosition(),r=document.querySelector('#cy').getBoundingClientRect();return {x:r.x+p.x,y:r.y+p.y}}")
          page.mouse.click(pos['x'],pos['y']);page.wait_for_selector('.molecule-drawing')
          assert 'CHEMBL8' in page.locator('#molecule-selection').inner_text()
          assert page.locator('#molecule-smiles').inner_text()==page.evaluate("graph.getElementById('CHEMBL8').data('record').props.smiles")
          assert page.locator('.molecule-drawing line').count()>0
          page.keyboard.press('Escape')
          ids=page.evaluate("graphOverview.nodes.filter(n=>n.type==='Compound').map(n=>n.id)")
          for identity in [ids[i] for i in [1,10,100,200,300,400,500,592]]+['CHEMBL454950']:
           page.evaluate('(id)=>{graph.getElementById(id).emit("tap");}',identity)
           assert identity in page.locator('#molecule-selection').inner_text()
           assert page.locator('.molecule-drawing').count()==1,(identity,page.locator('#structure-render-status').inner_text())
           assert page.locator('.molecule-drawing line').count()>0,identity
          page.keyboard.press('Escape');page.locator('#structure .panel-focus').click()
          page.keyboard.press('Escape')
          page.evaluate("() => {selectGraphMolecule({id:'invalid-fixture',name:'Invalid test fixture',source:'test',props:{smiles:'not-a-smiles'}});}")
          assert 'could not be drawn' in page.locator('#structure-render-status').inner_text()
          assert page.locator('#molecule-smiles').inner_text()=='not-a-smiles'
          page.click('#molecule-reset');assert page.locator('.molecule-image').count()==1
          # Organisms never get rendered as molecules.
          page.evaluate("() => {graph.getElementById('CHEMBL354').emit('tap');}");assert page.locator('.molecule-image').count()==1
          page.keyboard.press('Escape')
          page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
          assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
          assert not page.locator('.pane-divider').first.is_visible()
          page.locator('#kg .panel-focus').click();page.wait_for_timeout(150)
          assert page.locator('#kg').bounding_box()['width']>360
          assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
          page.keyboard.press('Escape')
          assert not errors,errors
          assert not writes,writes
          assert not external,external
          browser.close()
        finally:p.terminate();p.wait(timeout=10)
