"""The live backend for the demo page: runs agent.propose on a typed question and streams the trace to the page
stage by stage (server-sent events). Also serves slides/, so the deck and the demo page come from the same origin.

    python -m agent.server                      # http://localhost:8008/talks/biohack/demo/  (and the deck one level up)
    python -m agent.server --model moonshotai/Kimi-K3 --record slides/talks/biohack/demo/runs

    POST /api/run   {"query": "...", "model"?: "...", "fresh"?: true}   -> {"id", "model", "cached"}
    GET  /api/runs/{id}/events                                           -> text/event-stream of trace events
    GET  /api/runs/{id}                                                  -> the trace so far, as JSON
    GET  /api/health                                                     -> {"ok", "model", "models", "graphs"}

Events are those of agent.trace.Trace (lookup, call, reasoning, proposal, plate, error, done), one per message,
numbered so a dropped connection resumes with Last-Event-ID. A finished run is cached by (query, model): asking
the same question again replays it at once, which is what a rehearsed demo wants; `fresh: true` reruns.
Every run is saved to agent/out/live/<id>.json, and to --record/<id>.js for the page's static mode.
"""
import argparse
import asyncio
import json
import queue
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from wwtn.llm import DEFAULT_MODEL, EVAL_MODELS
from wwtn.schema import Question

from .propose import propose
from .tools import REPO, KnowledgeBase
from .trace import Trace, slug

OUT = REPO / "agent" / "out" / "live"


class RunRequest(BaseModel):
    query: str
    model: str | None = None
    fresh: bool = False


class Run:
    def __init__(self, id: str, query: str, model: str):
        self.id, self.query, self.model = id, query, model
        self.events: list[tuple[str, object]] = []
        self.listeners: list[queue.Queue] = []
        self.finished = False
        self.trace: Trace | None = None

    def push(self, event: str, payload) -> None:
        self.events.append((event, payload))
        if event in ("done", "error"):
            self.finished = True
        for q in self.listeners:
            q.put((event, payload))


class Server:
    def __init__(self, model: str, kg: str | None, record: Path | None, models: list[str] | None = None):
        self.model, self.record = model, record
        self.models = list(dict.fromkeys([model, *(models or EVAL_MODELS)]))   # the page's dropdown, default first
        self.kb = KnowledgeBase(kg)
        self.runs: dict[str, Run] = {}
        self.by_key: dict[tuple[str, str], str] = {}
        self.lock = threading.Lock()

    def start(self, req: RunRequest) -> tuple[Run, bool]:
        model = req.model or self.model
        key = (req.query.strip().lower(), model)
        with self.lock:
            cached = self.runs.get(self.by_key.get(key, ""))
            if cached and not req.fresh and (not cached.finished or cached.events[-1][0] == "done"):
                return cached, True
            run_id = f"{slug(req.query)[:40]}-{int(time.time())}"
            run = self.runs[run_id] = Run(run_id, req.query, model)
            self.by_key[key] = run_id
        threading.Thread(target=self.work, args=(run,), daemon=True).start()
        return run, False

    def work(self, run: Run) -> None:
        note = "Graphs: hand-written sample (agent/data/sample_kg)" if self.kb.sample else ""   # TODO(final)
        trace = run.trace = Trace(run.id, run.query, run.model, note=note)
        trace.on(run.push)
        try:
            propose(Question(id=run.id, text=run.query), model=run.model, kb=self.kb, trace=trace)
        except Exception as e:   # the page shows the message; the trace keeps what was done
            if not run.finished:
                trace.fail(f"{type(e).__name__}: {e}")
        trace.write_json(OUT / f"{run.id}.json")
        if self.record and trace.data.get("proposal"):
            trace.write_js(self.record / f"{run.id}.js")


def build(server: Server, slides: Path) -> FastAPI:
    app = FastAPI(title="What we test next: live demo backend")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        """The page and its scripts change often while we work on them: make browsers revalidate every time."""
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/api/health")
    def health():
        return {"ok": True, "model": server.model, "models": server.models, "graphs": server.kb.source}

    @app.post("/api/run")
    def start(req: RunRequest):
        if not req.query.strip():
            raise HTTPException(400, "empty query")
        run, cached = server.start(req)
        return {"id": run.id, "model": run.model, "cached": cached}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        run = server.runs.get(run_id)
        if not run:
            raise HTTPException(404, "no such run")
        return {"id": run.id, "query": run.query, "model": run.model, "finished": run.finished,
                "trace": run.trace.to_dict() if run.trace else None}

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request):
        run = server.runs.get(run_id)
        if not run:
            raise HTTPException(404, "no such run")
        last = int(request.headers.get("last-event-id") or -1)

        async def gen():
            q: queue.Queue = queue.Queue()
            run.listeners.append(q)
            try:
                # everything so far (after Last-Event-ID), then whatever arrives
                n = 0
                for n, (event, payload) in enumerate(run.events):
                    if n > last:
                        yield f"id: {n}\nevent: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                sent = len(run.events)
                if run.finished:
                    return
                while True:
                    try:
                        event, payload = await asyncio.to_thread(q.get, True, 15)
                    except queue.Empty:
                        yield ": keep-alive\n\n"
                        continue
                    yield f"id: {sent}\nevent: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    sent += 1
                    if event in ("done", "error"):
                        return
            finally:
                run.listeners.remove(q)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    if slides.is_dir():
        app.mount("/", StaticFiles(directory=str(slides), html=True), name="slides")
    return app


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve the demo page with a live agent behind it.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8008)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="default model for live runs")
    ap.add_argument("--models", help="comma-separated model IDs the page offers (default: wwtn.llm.EVAL_MODELS)")
    ap.add_argument("--kg", help="folder holding biology/graph and protocols/graph (default: kg/)")
    ap.add_argument("--record", type=Path, help="also write each finished run as <folder>/<id>.js for the page")
    ap.add_argument("--slides", type=Path, default=REPO / "slides", help="static folder to serve at / (default: slides/)")
    a = ap.parse_args()
    import uvicorn
    server = Server(a.model, a.kg, a.record, a.models.split(",") if a.models else None)
    print(f"model {server.model} · graphs {server.kb.source}")
    print(f"demo: http://{a.host}:{a.port}/talks/biohack/demo/   deck: http://{a.host}:{a.port}/talks/biohack/")
    uvicorn.run(build(server, a.slides), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
