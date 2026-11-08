"""Bounded replay UI smoke; starts/stops only its own temporary server."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from playwright.sync_api import sync_playwright
from demo.harness.paths import ROOT, DEMO


class BrowserTests(unittest.TestCase):
    def test_public_view_hides_controls_and_loads_only_published_results(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as logs:
            published = Path(directory) / 'sessions.json'
            published.write_text('["ses_e46864406ffeAYxrmbT9XhIE2G"]')
            process = subprocess.Popen([sys.executable, '-m', 'demo.harness.stage.public_view'], cwd=ROOT,
                env={**os.environ, 'DEMO_REPLAY': '1', 'PUBLIC_VIEW_PORT': str(port),
                     'DEMO_PUBLISHED_SESSIONS_FILE': str(published)}, stdout=logs, stderr=logs)
            try:
                url = f'http://127.0.0.1:{port}'
                for _ in range(50):
                    if process.poll() is not None:
                        self.fail('Public viewer exited during startup')
                    try:
                        urllib.request.urlopen(url + '/api/health', timeout=1); break
                    except OSError:
                        time.sleep(.1)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
                    try:
                        page = browser.new_page(viewport={'width': 390, 'height': 844})
                        errors, failures = [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('response', lambda r: failures.append(r.status) if r.status >= 400 else None)
                        page.goto(url+'/results')
                        page.wait_for_selector('.well')
                        self.assertEqual(page.locator('.well').count(), 96)
                        self.assertFalse(page.locator('.composer').is_visible())
                        self.assertFalse(page.locator('#keys').is_visible())
                        self.assertFalse(page.locator('#model').is_visible())
                        self.assertEqual(page.locator('#saved option').count(), 1)
                        self.assertIn('view only', page.locator('#connection').inner_text())
                        recording = page.request.get(url + '/api/recording').json()
                        if recording.get('available'):
                            # Poll browser properties without wait_for_function's eval;
                            # the viewer intentionally disallows unsafe-eval in CSP.
                            video = page.locator('#robot-video')
                            for _ in range(50):
                                if video.evaluate('(v) => v.readyState >= 2'): break
                                page.wait_for_timeout(100)
                            self.assertGreaterEqual(video.evaluate('(v) => v.readyState'), 2)
                            self.assertIn('Recorded', page.locator('#recording-card').inner_text())
                            self.assertAlmostEqual(video.evaluate('(v) => v.duration'), 30, delta=.1)
                            video.evaluate('(v) => v.play()')
                            for _ in range(50):
                                if video.evaluate('(v) => v.currentTime > .5'): break
                                page.wait_for_timeout(100)
                            self.assertGreater(video.evaluate('(v) => v.currentTime'), .5)
                            video.evaluate('(v) => {v.pause(); v.currentTime = 20}')
                            for _ in range(50):
                                if not video.evaluate('(v) => v.seeking'): break
                                page.wait_for_timeout(100)
                            self.assertFalse(video.evaluate('(v) => v.seeking'))
                            self.assertAlmostEqual(video.evaluate('(v) => v.currentTime'), 20, delta=.1)
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                        self.assertEqual(errors, [])
                        self.assertEqual(failures, [])
                    finally:
                        browser.close()
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait()

    def test_replay_desktop_mobile_downloads_and_slide_entry(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        with tempfile.TemporaryFile() as logs:
            process = subprocess.Popen([sys.executable,'-m','demo.harness.stage.server'],cwd=ROOT,
                env={**os.environ,'DEMO_REPLAY':'1','STAGE_PORT':str(port)},stdout=logs,stderr=logs)
            try:
                url=f'http://127.0.0.1:{port}'
                for _ in range(50):
                    if process.poll() is not None:
                        logs.seek(0); self.fail(logs.read().decode())
                    try:
                        urllib.request.urlopen(url+'/api/health',timeout=1); break
                    except OSError: time.sleep(.1)
                with sync_playwright() as playwright:
                    browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
                    try:
                        page=browser.new_page(viewport={'width':1600,'height':1000})
                        errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                        page.goto(url+'/planner')
                        page.wait_for_function("document.querySelector('#saved').options.length > 1")
                        page.select_option('#saved','ses_e46864406ffeAYxrmbT9XhIE2G')
                        page.wait_for_selector('.well')
                        self.assertEqual(page.locator('.well').count(),96)
                        self.assertEqual(page.locator('#run-select option').count(),4)
                        self.assertTrue(page.locator('#submit').is_disabled())
                        self.assertIn('Saved artifacts',page.locator('#view-label').inner_text())
                        page.locator('.well').first.click()
                        self.assertIn('A1',page.locator('#well-detail').inner_text())
                        page.select_option('#run-select','run-004')
                        self.assertIn('hash verified',page.locator('#design').inner_text())
                        href=page.get_by_role('link',name='OT-2 protocol',exact=True).get_attribute('href')
                        response=page.request.get(url+href)
                        self.assertEqual(response.status,200)
                        self.assertIn('def run(',response.text())
                        page.set_viewport_size({'width':390,'height':844})
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                        page.reload();page.select_option('#saved','ses_e46864406ffeAYxrmbT9XhIE2G')
                        page.wait_for_selector('.well');self.assertEqual(page.locator('.well').count(),96)
                        self.assertFalse(errors,errors)
                        # Original static entry still resolves through the unchanged slide symlink.
                        entry=ROOT/'slides/talks/biohack/demo/index.html'
                        self.assertEqual(entry.resolve(),DEMO/'index.html')
                        page.goto(entry.as_uri()+'?theme=dark')
                        self.assertTrue(page.locator('body').inner_text())
                    finally: browser.close()
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()
