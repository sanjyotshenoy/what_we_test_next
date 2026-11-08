"""Memory-only BYOK ownership and isolated, cancellable worker processes."""
import asyncio
from collections import deque
import hashlib
import json
import os
import secrets
import shutil
import signal
import time

from aiohttp import web
from demo.harness.paths import ROOT, DEMO
from demo.harness.stage import planning_view

COOKIE = 'demo_run_owner'
TTL = 3600
TIMEOUT = 900


def worker_environment():
    # No inherited provider keys, config overrides, dotenv or OpenCode auth.
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR') if k in os.environ}
    env['PYTHON_DOTENV_DISABLED'] = '1'
    return env


def owner(request):
    token = request.cookies.get(COOKIE, '')
    return hashlib.sha256(token.encode()).hexdigest() if len(token) == 64 else None


class PublicRuns:
    def __init__(self):
        self.jobs = {}
        self.starts = deque()

    def visible(self, request, session):
        job = self.jobs.get(session)
        return bool(job and job['owner'] == owner(request) and job['expires'] > time.monotonic())

    def public(self, job):
        return {k: job[k] for k in ('session', 'state', 'message', 'model', 'question')}

    async def start(self, request):
        try:
            body = await request.json()
        except (ValueError, TypeError):
            raise web.HTTPBadRequest(text='Expected a JSON object.') from None
        if not isinstance(body, dict):
            raise web.HTTPBadRequest(text='Expected a JSON object.')
        models = {m['id'] for m in json.loads((DEMO / 'sequential-models.json').read_text())['models']}
        key, question, model = body.get('key'), body.get('question'), body.get('model')
        if (not isinstance(key, str) or not 8 <= len(key.strip()) <= 512 or
                not isinstance(question, str) or not 10 <= len(question.strip()) <= 12000 or not isinstance(model, str) or model not in models):
            raise web.HTTPBadRequest(text='Enter a key, a question (10–12000 characters), and an offered model.')
        now = time.monotonic()
        while self.starts and self.starts[0][0] < now - TTL:
            self.starts.popleft()
        identity = owner(request)
        active = [j for j in self.jobs.values() if not j['task'].done()]
        if len(active) >= 2 or any(j['owner'] == identity for j in active):
            raise web.HTTPTooManyRequests(text='A run is active. Wait or stop your current run.')
        if len(self.starts) >= 20 or sum(o == identity for _, o in self.starts) >= 5:
            raise web.HTTPTooManyRequests(text='Run limit reached. Please try again later.')
        token = request.cookies.get(COOKIE) if identity else secrets.token_hex(32)
        identity = hashlib.sha256(token.encode()).hexdigest()
        session = 'public_' + secrets.token_hex(16)
        job = dict(session=session, owner=identity, state='starting', message='Starting isolated run…',
                   model=model, question=question.strip(), expires=now + TTL)
        self.jobs[session] = job
        self.starts.append((now, identity))
        job['task'] = asyncio.create_task(self.execute(job, {'key': key.strip(), 'question': question.strip(), 'model': model}))
        response = web.json_response(self.public(job), status=202)
        response.set_cookie(COOKIE, token, httponly=True, secure=request.host.split(':')[0] not in ('127.0.0.1', 'localhost'),
                            samesite='Strict', max_age=TTL, path='/')
        return response

    async def execute(self, job, payload):
        process = None
        try:
            async with asyncio.timeout(TIMEOUT):
                process = await asyncio.create_subprocess_exec(
                    str(DEMO / '.venv/bin/python'), '-m', 'demo.harness.public_worker', job['session'],
                    cwd=ROOT, env=worker_environment(), stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
                process.stdin.write(json.dumps(payload).encode() + b'\n')
                payload.clear()
                await process.stdin.drain()
                process.stdin.close()
                while line := await process.stdout.readline():
                    event = json.loads(line)
                    if event.get('state') in ('running', 'finished', 'failed'):
                        job.update(state=event['state'], message=event['message'])
                await process.wait()
                if job['state'] not in ('finished', 'failed'):
                    job.update(state='failed', message='The worker exited before completion.')
        except asyncio.CancelledError:
            job.update(state='stopped', message='Stopped. No further model calls will be made.')
            raise
        except TimeoutError:
            job.update(state='failed', message='The 15-minute limit was reached.')
        except Exception:
            job.update(state='failed', message='The run could not complete. No automatic retry was made.')
        finally:
            payload.clear()
            if process:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()

    async def get(self, request):
        session = request.match_info['session']
        if not self.visible(request, session):
            raise web.HTTPNotFound()
        return web.json_response(self.public(self.jobs[session]))

    async def stop(self, request):
        session = request.match_info['session']
        if not self.visible(request, session):
            raise web.HTTPNotFound()
        task = self.jobs[session]['task']
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self.jobs[session].update(state='stopped', message='Stopped. No further model calls will be made.')
        return web.json_response(self.public(self.jobs[session]))

    async def lifecycle(self, app):
        async def sweep():
            while True:
                await asyncio.sleep(30)
                for session, job in list(self.jobs.items()):
                    if job['expires'] <= time.monotonic() and job['task'].done():
                        await asyncio.to_thread(shutil.rmtree, planning_view.session_path(session), True)
                        del self.jobs[session]
        sweeper = asyncio.create_task(sweep())
        yield
        sweeper.cancel()
        tasks = [j['task'] for j in self.jobs.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(sweeper, *tasks, return_exceptions=True)
        for session in self.jobs:
            await asyncio.to_thread(shutil.rmtree, planning_view.session_path(session), True)
