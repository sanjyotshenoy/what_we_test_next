"""Stage server: the live demo page + a bridge to the OpenCode agent.

    .venv/bin/python -m demo.harness.stage.server            # or harness/stage.sh (also starts OpenCode)

Browser  <-SSE /api/stream-  stage server  <-SSE /event-  OpenCode (agent)  ->  Nebius / local vLLM
Tools (harness/tools.py) POST /api/panel  ->  stage server  ->  every open page (KG, structure, plate, robot)

Binds 127.0.0.1 and the Tailscale IPv4 (not 0.0.0.0: hackathon Wi-Fi), port $STAGE_PORT (7100).
API keys are never sent to the browser; the page only ever sees profile names.
"""
import asyncio
import base64
import json
import os
import subprocess
import time
from pathlib import Path

import aiohttp
from aiohttp import web
from demo.harness.stage import planning_view

HERE = Path(__file__).resolve().parent
from demo.harness.paths import ROOT, DEMO
STATIC = HERE / "static"
OC_DIR = DEMO / "harness" / "opencode"
KEYS = OC_DIR / "private" / "keys.json"          # {"name": "key"}; mode 600; optional
OC_URL = f"http://127.0.0.1:{os.environ.get('OPENCODE_PORT', '4096')}"
PORT = int(os.environ.get("STAGE_PORT", "7100"))
REPLAY = os.environ.get("DEMO_REPLAY") == "1"
AGENT = os.environ.get("STAGE_AGENT", "planner")
PROVIDERS = ("nebius", "spark-qwen")


def oc_auth() -> dict:
    pw = (OC_DIR / "private" / "server_password").read_text().strip()
    return {"Authorization": "Basic " + base64.b64encode(f"opencode:{pw}".encode()).decode()}


class Hub:
    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.session_id: str | None = None
        self.model = {"providerID": "nebius", "modelID": os.environ.get("HARNESS_NEBIUS_MODEL", "openai/gpt-oss-120b")}
        self.key_profile: str | None = None
        self.panels: dict[str, list] = {"kg": [], "structure": [], "plate": []}   # replayed on page reload (not robot)
        self.oc_ok = False

    def send(self, ev: dict):
        for q in list(self.clients):
            if q.qsize() < 1000:
                q.put_nowait(ev)


hub = Hub()


# ---------------------------------------------------------------- OpenCode bridge
async def oc(method: str, path: str, body=None, timeout=30):
    if REPLAY:
        raise web.HTTPConflict(text="Replay mode: live agent operations are disabled")
    async with aiohttp.ClientSession(headers=oc_auth()) as s:
        async with s.request(method, OC_URL + path, json=body, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            text = await r.text()
            if r.status >= 400:
                raise web.HTTPBadGateway(text=f"OpenCode {method} {path}: {r.status} {text[:300]}")
            return json.loads(text) if text else None


FORWARD = {"message.part.updated", "message.part.delta", "message.updated", "session.status", "session.idle",
           "session.error", "permission.updated", "permission.asked"}


async def oc_events():
    """Follow OpenCode's event stream forever; forward our session's events to the pages."""
    backoff = 1
    while True:
        try:
            async with aiohttp.ClientSession(headers=oc_auth()) as s:
                async with s.get(OC_URL + "/event", timeout=aiohttp.ClientTimeout(total=None, sock_read=90)) as r:
                    hub.oc_ok = True
                    hub.send({"type": "status", "opencode": True})
                    backoff = 1
                    async for raw in r.content:
                        line = raw.decode(errors="replace").strip()
                        if not line.startswith("data:"):
                            continue
                        ev = json.loads(line[5:])
                        if ev.get("type") not in FORWARD:
                            continue
                        pr = ev.get("properties", {})
                        sid = pr.get("sessionID") or pr.get("part", {}).get("sessionID") or pr.get("info", {}).get("sessionID")
                        if not hub.session_id or sid != hub.session_id:
                            continue
                        hub.send({"type": "oc", "event": ev})
        except Exception as e:  # noqa: BLE001 - reconnect on anything
            if hub.oc_ok:
                hub.send({"type": "status", "opencode": False, "error": repr(e)[:200]})
            hub.oc_ok = False
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)


async def ensure_session():
    if not hub.session_id:
        info = await oc("POST", "/session", {"title": f"stage {time.strftime('%H:%M:%S')}"})
        hub.session_id = info["id"]
    return hub.session_id


# ---------------------------------------------------------------- keys (never echoed)
def load_keys() -> dict:
    try:
        return json.loads(KEYS.read_text())
    except (OSError, ValueError):
        return {}


def save_keys(d: dict):
    KEYS.parent.mkdir(mode=0o700, exist_ok=True)
    tmp = KEYS.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(d, f)
    os.replace(tmp, KEYS)


def seed_keys():
    """First run: import demo.harness/.env's key as profile 'default' so the picker is never empty."""
    d = load_keys()
    if d:
        return
    env = DEMO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("NEBIUS_API_KEY=") and line.split("=", 1)[1].strip():
                save_keys({"default": line.split("=", 1)[1].strip()})


async def apply_key(name: str, key: str):
    if hub.session_id:
        await oc('POST', f'/session/{hub.session_id}/abort')
    await oc("PUT", "/auth/nebius", {"type": "api", "key": key})
    await oc("POST", "/instance/dispose")        # without this the old key stays cached
    hub.key_profile = name
    hub.session_id = None                        # dispose resets the instance; start fresh


# ---------------------------------------------------------------- HTTP API
def local_only(request):
    if request.remote not in ("127.0.0.1", "::1"):
        raise web.HTTPForbidden(text="local tools only")


async def api_panel(request):
    local_only(request)
    ev = await request.json()
    name = ev.get("panel")
    if name in hub.panels:
        if ev.get("op") in ("reset",):
            hub.panels[name] = []
        else:
            hub.panels[name] = (hub.panels[name] + [ev])[-200:]
    hub.send({"type": "panel", **ev})
    return web.json_response({"ok": True})


async def api_stream(request):
    resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache",
                                       "X-Accel-Buffering": "no"})
    await resp.prepare(request)
    q: asyncio.Queue = asyncio.Queue()
    hub.clients.add(q)
    try:
        hello = {"type": "hello", "opencode": hub.oc_ok, "session": hub.session_id, "model": hub.model,
                 "key_profile": hub.key_profile, "panels": hub.panels, "replay": REPLAY}
        await resp.write(f"data: {json.dumps(hello)}\n\n".encode())
        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=15)
                await resp.write(f"data: {json.dumps(ev)}\n\n".encode())
            except asyncio.TimeoutError:
                await resp.write(b": ping\n\n")
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        hub.clients.discard(q)
    return resp


async def api_prompt(request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise web.HTTPBadRequest(text="empty prompt")
    sid = await ensure_session()
    await oc("POST", f"/session/{sid}/prompt_async",
             {"agent": AGENT, "model": hub.model, "parts": [{"type": "text", "text": text}]})
    return web.json_response({"session": sid})


async def api_transcript(request):
    """The current session's messages, so a reloaded page can redraw the transcript."""
    if not hub.session_id:
        return web.json_response([])
    return web.json_response(await oc("GET", f"/session/{hub.session_id}/message"))


async def api_activity(request):
    """Visible answers and tool outcomes only; no reasoning or full tool payloads."""
    if not hub.session_id:
        return web.json_response({'session': None, 'items': [], 'cost': 0})
    sid = hub.session_id
    messages = await oc('GET', f'/session/{sid}/message')
    items, cost = [], 0
    for message in messages:
        info = message.get('info', {})
        cost += info.get('cost', 0) or 0
        if info.get('error'):
            items.append({'type': 'error', 'text': str(info['error'].get('data', {}).get('message', info['error']))[:500]})
        for part in message.get('parts', []):
            if part.get('type') == 'text' and info.get('role') == 'assistant':
                items.append({'type': 'text', 'text': part.get('text', '')})
            elif part.get('type') == 'tool':
                state = part.get('state', {})
                item = {'type': 'tool', 'name': part.get('tool'), 'status': state.get('status')}
                try:
                    output = json.loads(state.get('output', '{}'))
                    item['outcome'] = output.get('status') or ('error' if output.get('error') else None)
                    item['details'] = output.get('errors') or output.get('message') or state.get('error')
                except (ValueError, TypeError, AttributeError):
                    item['details'] = state.get('error')
                items.append(item)
    return web.json_response({'session': sid, 'items': items[-60:], 'cost': cost})


async def api_new(request):
    if hub.session_id:
        await oc("POST", f"/session/{hub.session_id}/abort")
    hub.session_id = None
    for k in hub.panels:
        hub.panels[k] = []
    hub.send({"type": "reset"})
    return web.json_response({"ok": True})


async def api_abort(request):
    if hub.session_id:
        await oc("POST", f"/session/{hub.session_id}/abort")
    return web.json_response({"ok": True})


async def api_models(request):
    if REPLAY:
        return web.json_response({"models": [], "current": hub.model, "replay": True})
    # Only the models named in our opencode.json (OpenCode merges in the provider's whole public catalogue).
    conf = json.loads((OC_DIR / "opencode.json").read_text())["provider"]
    cfg = await oc("GET", "/config/providers")
    out = []
    for p in cfg.get("providers", []):
        if p["id"] in PROVIDERS:
            out += [{"providerID": p["id"], "modelID": m, "name": v.get("name", m)} for m, v in p["models"].items()
                    if m in conf.get(p["id"], {}).get("models", {})]
    return web.json_response({"models": out, "current": hub.model})


async def api_model(request):
    body = await request.json()
    conf = json.loads((OC_DIR / 'opencode.json').read_text())['provider']
    if body.get('modelID') not in conf.get(body.get('providerID'), {}).get('models', {}):
        raise web.HTTPBadRequest(text='Unknown configured model')
    hub.model = {"providerID": body["providerID"], "modelID": body["modelID"]}
    hub.send({"type": "model", "model": hub.model})
    return web.json_response({"model": hub.model})


async def api_keys_get(request):
    return web.json_response({"profiles": sorted(load_keys()), "active": hub.key_profile})


async def api_keys_post(request):
    body = await request.json()
    name = (body.get("name") or "").strip()[:40]
    key = (body.get("key") or "").strip()
    keys = load_keys()
    if key:
        if not name:
            raise web.HTTPBadRequest(text="name the key (e.g. your first name)")
        if body.get("save", True):
            keys[name] = key
            save_keys(keys)
    elif name in keys:
        key = keys[name]
    else:
        raise web.HTTPBadRequest(text="unknown profile and no key given")
    await apply_key(name, key)
    hub.send({"type": "key", "active": name})
    return web.json_response({"active": name, "profiles": sorted(load_keys())})


async def api_health(request):
    return web.json_response({"ok": True, "opencode": hub.oc_ok, "session": hub.session_id, "agent": AGENT})


async def api_planning(request):
    session = request.query.get('session') or hub.session_id
    if not session:
        return web.json_response({'session': None, 'evidence': [], 'batches': []})
    try:
        data = await asyncio.to_thread(planning_view.snapshot, session)
    except ValueError as exc:
        raise web.HTTPBadRequest(text=str(exc))
    data['view'] = 'live' if session == hub.session_id else 'saved artifacts'
    return web.json_response(data)


async def api_planning_sessions(request):
    return web.json_response(await asyncio.to_thread(planning_view.sessions))


async def api_artifact(request):
    try:
        path = planning_view.artifact_path(request.match_info['session'], request.match_info['batch'],
                                           request.match_info['filename'])
    except ValueError as exc:
        raise web.HTTPNotFound(text=str(exc))
    return web.FileResponse(path, headers={'Content-Disposition': f'attachment; filename="{path.name}"',
                                          'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


async def index(request):
    name = 'index.html' if request.path == '/legacy' else 'planner.html'
    return web.FileResponse(STATIC / name, headers={"Cache-Control": "no-cache"})


async def on_cleanup(app):
    if "oc_task" in app:
        app["oc_task"].cancel()
        await asyncio.gather(app["oc_task"], return_exceptions=True)


async def on_start(app):
    if REPLAY:
        return
    seed_keys()
    keys = load_keys()
    if keys and "default" in keys:
        await apply_key("default", keys["default"])
    app["oc_task"] = asyncio.create_task(oc_events())


def bind_hosts() -> list[str]:
    hosts = ["127.0.0.1"]
    try:
        ts = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5).stdout.split()
        hosts += ts[:1]
    except Exception:
        pass
    return hosts


@web.middleware
async def replay_read_only(request, handler):
    if REPLAY and request.method not in ('GET', 'HEAD'):
        raise web.HTTPConflict(text='Replay mode is read-only')
    return await handler(request)


def make_app():
    app = web.Application(middlewares=[replay_read_only])
    app.add_routes([
        web.get("/", index),
        web.get("/legacy", index),
        web.get("/api/planning", api_planning),
        web.get("/api/planning/sessions", api_planning_sessions),
        web.get("/api/artifacts/{session}/{batch}/{filename:.*}", api_artifact),
        web.get("/api/stream", api_stream),
        web.get("/api/health", api_health),
        web.post("/api/panel", api_panel),
        web.post("/api/prompt", api_prompt),
        web.post("/api/new", api_new),
        web.get("/api/transcript", api_transcript),
        web.get("/api/activity", api_activity),
        web.post("/api/abort", api_abort),
        web.get("/api/models", api_models),
        web.post("/api/model", api_model),
        web.get("/api/keys", api_keys_get),
        web.post("/api/keys", api_keys_post),
        web.static("/static", STATIC, show_index=False),
    ])
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    hosts = bind_hosts()
    print(f"stage: http://{hosts[-1]}:{PORT}/  (bound {', '.join(hosts)}; OpenCode {OC_URL})", flush=True)
    web.run_app(make_app(), host=hosts, port=PORT, print=None)
