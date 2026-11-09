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

    def public(self, job, after=None):
        result = {k: job[k] for k in ('session', 'state', 'message', 'model', 'question')}
        result.update(stage=job.get('stage'), turn=job.get('turn', 0), steps=job.get('steps', {}))
        if after is not None:
            events = job.get('events', [])
            result.update(events=[e for e in events if e['id'] > after], last_event=job.get('sequence', 0),
                          events_truncated=bool(events and after < events[0]['id'] - 1))
        return result

    def record(self, job, event):
        if event.get('state') not in ('running', 'finished', 'failed'):
            return
        job.update(state=event['state'], message=str(event.get('message', ''))[:500])
        previous_stage = job.get('stage')
        stage = event.get('stage')
        if stage in ('model', 'context', 'biology', 'literature', 'proposal', 'checks', 'protocols', 'simulation'):
            job['stage'] = stage
        if isinstance(event.get('turn'), int):
            job['turn'] = event['turn']
        kind = event.get('kind', 'status')
        steps = job.setdefault('steps', {})
        if kind in ('model_start', 'tool_start', 'stage') and stage:
            steps[stage] = 'running'
        elif kind in ('model_end', 'proposal') and stage:
            steps[stage] = 'returned'
        elif kind == 'tool_result' and stage:
            steps[stage] = 'failed' if event.get('outcome') == 'failed' else 'returned'
            if event.get('tool') == 'planning_submit' and (event.get('outcome') != 'failed' or previous_stage == 'protocols'):
                steps['protocols'] = steps[stage]
        job['sequence'] = job.get('sequence', 0) + 1
        clean = {k: event[k] for k in ('kind', 'tool', 'stage', 'turn', 'outcome', 'truncated') if k in event}
        clean.update(id=job['sequence'], message=job['message'], state=job['state'],
                     elapsed=round(time.monotonic()-job.setdefault('started', time.monotonic()), 1))
        clean['text'] = str(event.get('text', ''))[:6000]
        events = job.setdefault('events', deque())
        events.append(clean)
        job['event_chars'] = job.get('event_chars', 0) + len(clean['text'])
        while len(events) > 2000 or job['event_chars'] > 2_000_000:
            job['event_chars'] -= len(events.popleft()['text'])

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
                   model=model, question=question.strip(), expires=now + TTL, started=now)
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
                    self.record(job, event)
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
        try:
            after = max(0, int(request.query['after'])) if 'after' in request.query else None
        except ValueError:
            raise web.HTTPBadRequest(text='Invalid event cursor.') from None
        return web.json_response(self.public(self.jobs[session], after))

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
