"""A trace of one run: what the demo page plays (format: demo/README.md).

The agent fills it as it goes (`set_lookup`, `add_call`, `add_reasoning`, `set_proposal`); every addition is
also sent to listeners (`trace.on(fn)`), which is how the live server streams a run to the page. At the end,
`write_js` writes a `runs/<id>.js` the page loads, `write_json` the same as JSON.

Stages the agent does not produce (procedure, protocol, simulation from execution/; validation from
benchmark/) are left out; the page skips stages whose data is missing.
"""
import json
import re
from pathlib import Path
from typing import Callable


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "run"


def plate_from(experiment: dict) -> dict:
    """The plate map the page draws, derived from the experiment: one row per replicate, the series across
    columns 1..n_points, then the controls."""
    n = min(int(experiment["n_points"]), 12)
    controls = {}
    for i, c in enumerate(experiment.get("controls", [])[:2]):
        col = n + 1 + i
        if col > 12:
            break
        controls[col] = "DMSO" if re.search(r"vehicle|dmso", c, re.I) else "positive"
    return {"rows": "ABCDEFGH"[: max(1, min(8, int(experiment.get("replicates", 3))))],
            "top_uM": experiment["top_concentration_uM"], "factor": experiment["dilution_factor"],
            "points": n, "controls": controls}


class Trace:
    def __init__(self, id: str, query: str, model: str, note: str = "", mock: bool = False):
        self.data = {"id": id, "query": query, "model": model, "mock": mock, "note": note,
                     "lookup": None, "calls": [], "reasoning": [], "thinking": [], "proposal": None, "plate": None}
        self.listeners: list[Callable[[str, object], None]] = []

    def on(self, fn: Callable[[str, object], None]) -> None:
        self.listeners.append(fn)

    def emit(self, event: str, payload) -> None:
        for fn in self.listeners:
            fn(event, payload)

    def set_lookup(self, lookup: dict) -> None:
        self.data["lookup"] = lookup
        self.emit("lookup", lookup)

    def add_call(self, call: dict) -> None:
        self.data["calls"].append(call)
        self.emit("call", call)

    def add_reasoning(self, text: str, thinking: str = "") -> None:
        """`text` is what the page shows (the model's reported reasoning); `thinking` the raw reasoning tokens
        when the model exposes them, kept in the trace but not shown."""
        self.data["reasoning"].append(text)
        self.data["thinking"].append(thinking)
        self.emit("reasoning", text)

    def set_proposal(self, proposal: dict) -> None:
        self.data["proposal"] = proposal
        self.emit("proposal", proposal)
        if proposal.get("experiment"):
            self.data["plate"] = plate_from(proposal["experiment"])
            self.emit("plate", self.data["plate"])

    def fail(self, message: str) -> None:
        self.data["error"] = message
        self.emit("error", {"message": message})

    def done(self) -> None:
        self.emit("done", {})

    def to_dict(self) -> dict:
        return {k: v for k, v in self.data.items() if v not in (None, [], "")}

    def to_js(self) -> str:
        head = ("// A trace of one run of agent/propose.py, for the demo page (format in ../README.md). Generated: "
                "do not edit by hand.\n")
        return head + "(window.DEMO_RUNS = window.DEMO_RUNS || []).push(" + json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + ");\n"

    def write_js(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_js(), encoding="utf-8")
        return path

    def write_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path
