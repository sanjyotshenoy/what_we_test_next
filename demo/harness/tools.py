"""Tool backends for the stage agent. OpenCode's custom tools (.opencode/tools/*.ts) call these:

    .venv/bin/python -m demo.harness.tools <tool> '<json args>'

Each prints a compact JSON result for the LLM and, where the tool shows something, posts a panel event to the
stage server (POST /api/panel on 127.0.0.1:$STAGE_PORT), which pushes it to every open stage page.
The KG is the seed graph (harness/stage/static/data/kg_seed.json) until the team KG is on main.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

from demo.harness.paths import ROOT, DEMO
DATA = DEMO / "harness" / "stage" / "static" / "data"
STAGE = f"http://127.0.0.1:{os.environ.get('STAGE_PORT', '7100')}"


def panel(event: dict) -> bool:
    try:
        req = urllib.request.Request(f"{STAGE}/api/panel", data=json.dumps(event).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3).read()
        return True
    except Exception:
        return False        # the agent still gets its answer if no stage page is up


def kg():
    g = json.loads((DATA / "kg_seed.json").read_text())
    nodes = {n["id"]: n for n in g["nodes"]}
    # The held-out edge is the answer: the agent must never see it.
    edges = [e for e in g["edges"] if not e.get("held_out")]
    return nodes, edges


def kg_search(query: str, **_):
    nodes, _ = kg()
    q = query.lower().strip()
    hits = [n for n in nodes.values() if q in n["name"].lower() or q == n["id"].lower()]
    if not hits:   # fall back to word matches ("nilotinib KIT activity" -> nilotinib, KIT)
        stop = {"the", "and", "kinase", "activity", "inhibitor", "inhibition", "of", "on", "for", "with"}
        words = [w for w in q.replace(",", " ").split() if len(w) > 2 and w not in stop]
        hits = [n for n in nodes.values()
                if any(w == n["name"].lower() or w == n["id"].lower() or w in n["name"].lower().split() for w in words)]
    panel({"panel": "kg", "op": "highlight", "ids": [n["id"] for n in hits], "style": "found"})
    return {"query": query, "matches": hits}


def kg_neighbors(id: str, rel: str | None = None, **_):
    nodes, edges = kg()
    if id not in nodes:
        return {"error": f"unknown node {id}"}
    rows = []
    for e in edges:
        if rel and e["rel"] != rel:
            continue
        if e["src"] == id:
            rows.append({"rel": e["rel"], "dir": "out", "node": nodes[e["dst"]]})
        elif e["dst"] == id:
            rows.append({"rel": e["rel"], "dir": "in", "node": nodes[e["src"]]})
    ids = [id] + [r["node"]["id"] for r in rows]
    panel({"panel": "kg", "op": "highlight", "ids": ids, "focus": id, "style": "visited"})
    return {"id": id, "neighbors": rows}


def kg_annotate(ids: list, note: str, kind: str = "note", **_):
    """Pin a note to nodes (or 'src->dst' edges) on screen. kind: note | gap | evidence | proposal."""
    nodes, _ = kg()
    bad = [i for i in ids if "->" not in i and i not in nodes]
    ok = panel({"panel": "kg", "op": "annotate", "ids": ids, "note": note, "kind": kind})
    return {"annotated": [i for i in ids if i not in bad], "unknown": bad, "shown": ok}


def show_structure(pdb: str = "1T46", highlight_ligand: str | None = "STI", residues: list | None = None,
                   caption: str | None = None, **_):
    """Show a structure. Local file harness/stage/static/data/<PDB>.pdb if present, else fetched by the page."""
    pdb = pdb.upper()
    local = (DATA / f"{pdb}.pdb").exists()
    ok = panel({"panel": "structure", "pdb": pdb, "local": local, "ligand": highlight_ligand,
                "residues": residues or [], "caption": caption})
    return {"pdb": pdb, "source": "local cache" if local else "RCSB (needs network)", "shown": ok}


def plate_plan(top_uM: float, factor: float, n_points: int = 10, replicates: int = 8,
               controls: dict | None = None, title: str | None = None, **_):
    """Draw the planned plate: concentration per column, rows as replicates, plus control columns."""
    concs = [round(top_uM / factor ** k, 6) for k in range(n_points)]
    controls = controls or {"11": "growth control", "12": "sterility control"}
    ok = panel({"panel": "plate", "op": "plan", "concs_uM": concs, "rows": "ABCDEFGH"[:replicates],
                "controls": controls, "title": title})
    return {"columns": {str(i + 1): c for i, c in enumerate(concs)}, "controls": controls, "shown": ok,
            "lowest_uM": concs[-1]}


def robot_feed(action: str = "play", **_):
    """Start/stop the robot status replay (synced to the pre-recorded run video)."""
    ok = panel({"panel": "robot", "op": action})
    return {"robot_feed": action, "source": "pre-recorded run + simulator log (replay)", "shown": ok}


TOOLS = {f.__name__: f for f in (kg_search, kg_neighbors, kg_annotate, show_structure, plate_plan, robot_feed)}

if __name__ == "__main__":
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else {}
    try:
        out = TOOLS[name](**args)
    except Exception as e:  # report to the model instead of crashing the tool call
        out = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False))
