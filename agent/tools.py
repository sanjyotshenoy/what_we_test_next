"""The graph tools the agent calls: the two knowledge graphs (kg/README.md CSV format) behind a handful of
functions the LLM can call, each returning rows the demo page can show.

    kb = KnowledgeBase()                 # kg/*/graph/, or agent/data/sample_kg while those are missing
    kb.lookup("imatinib", "KIT")         # what the KB says on its own: a measurement, or "I don't know"
    kb.call("bio_kg_analogs", {...})     # one of TOOL_SPECS, by name, as the model calls it

Every tool returns {"summary", "columns", "rows", ...}: `rows` are what the page tabulates, the rest is extra
detail for the model. `KnowledgeBase.result_text()` renders one for the model.
"""
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KG_ROOT = REPO / "kg"
SAMPLE_ROOT = REPO / "agent" / "data" / "sample_kg"   # TODO(final): drop once kg/*/graph/ exist

# Gene symbols for the seed graph's 19 kinases: its Target nodes carry only a UniProt accession and a long
# protein name, so "BTK" or "AXL" in a question would not resolve.
# TODO(final): read these from UniProt in kg/biology/build_seed.py instead of hard-coding them here.
GENES = {"Q04771": "ACVR1", "O14965": "AURKA", "P48729": "CSNK1A1", "P78527": "PRKDC", "Q13627": "DYRK1A",
         "P51617": "IRAK1", "P53667": "LIMK1", "P45984": "MAPK9", "O43318": "MAP3K7", "O60285": "NUAK1",
         "Q9NRM7": "LATS2", "P57059": "SIK1", "Q9Y2K2": "SIK3", "Q8TF76": "GSG2", "P42345": "MTOR",
         "Q86UE8": "TLK2", "Q06187": "BTK", "Q12866": "MERTK", "P30530": "AXL"}

# The question types the seed protocol graph answers (ANSWERS edges), and the words a model may use for them.
QUESTION_TYPES = {"potency": "qtype:potency", "biochemical_potency": "qtype:potency",
                  "cellular_potency": "qtype:cellular_potency", "cellular_activity": "qtype:cellular_potency",
                  "cell_based": "qtype:cellular_potency", "binding": "qtype:binding", "affinity": "qtype:binding"}


class Graph:
    """One graph: nodes by ID, edges with src/dst/rel/props."""

    def __init__(self, folder: Path):
        self.folder = folder
        with open(folder / "nodes.csv", encoding="utf-8") as f:
            self.nodes = {r["id"]: {**r, "props": json.loads(r["props"] or "{}")} for r in csv.DictReader(f)}
        with open(folder / "edges.csv", encoding="utf-8") as f:
            self.edges = [{**r, "props": json.loads(r["props"] or "{}")} for r in csv.DictReader(f)]

    def out(self, src: str, rel: str | None = None) -> list[dict]:
        return [e for e in self.edges if e["src"] == src and (rel is None or e["rel"] == rel)]

    def into(self, dst: str, rel: str | None = None) -> list[dict]:
        return [e for e in self.edges if e["dst"] == dst and (rel is None or e["rel"] == rel)]

    def find(self, text: str, type_: str | None = None) -> dict | None:
        """A node by ID, exact name, or a name/gene that contains the text (case-insensitive)."""
        t = text.strip().lower()
        pool = [n for n in self.nodes.values() if type_ is None or n["type"] == type_]
        for n in pool:
            if n["id"].lower() == t or n["name"].lower() == t or str(n["props"].get("gene", "")).lower() == t:
                return n
        for n in pool:
            if t in n["name"].lower():
                return n
        return None

    def name(self, node_id: str) -> str:
        return self.nodes.get(node_id, {}).get("name", node_id)

    def classes(self, node_id: str) -> list[str]:
        """A target's class chain, most specific first: MEMBER_OF, then SUBCLASS_OF up to the root. The seed
        graph puts a target in its most specific ChEMBL class (BTK -> Tec family), while protocol templates hang
        off a broad one (Protein Kinase), so a template lookup has to walk the chain."""
        chain, seen = [], {node_id}
        edges = self.out(node_id, "MEMBER_OF") or self.out(node_id, "SUBCLASS_OF")
        while edges:
            nxt = edges[0]["dst"]
            if nxt in seen:
                break                                   # a cycle in the class table: stop where we are
            seen.add(nxt)
            chain.append(nxt)
            edges = self.out(nxt, "SUBCLASS_OF")
        return chain


def fmt_uM(nM: float) -> str:
    uM = nM / 1000
    return f"{uM:g} µM" if uM >= 1 else f"{nM:g} nM"


class KnowledgeBase:
    def __init__(self, root: Path | None = None):
        root = Path(root) if root else KG_ROOT
        folders = {g: root / g / "graph" for g in ("biology", "protocols")}
        self.sample = not all((p / "nodes.csv").exists() for p in folders.values())
        if self.sample:
            folders = {g: SAMPLE_ROOT / g for g in folders}
        self.bio, self.proto = Graph(folders["biology"]), Graph(folders["protocols"])
        for accession, gene in GENES.items():           # so a question can name a target by its gene symbol
            node = self.bio.nodes.get(accession)
            if node and not node["props"].get("gene"):
                node["props"]["gene"] = gene
        self._fps: dict | None = None                   # compound fingerprints, built on the first analog lookup

    @property
    def source(self) -> str:
        return "agent/data/sample_kg (hand-written stand-in)" if self.sample else "kg/*/graph"

    # --- the tools ------------------------------------------------------------------------------------------

    def lookup(self, compound: str, target: str) -> dict:
        """Stage 1, before the agent runs: does the biology KG hold a measurement for this pair?"""
        args = {"compound": compound, "target": target}
        c, t = self.bio.find(compound, "Compound"), self.bio.find(target, "Target")
        if not c or not t:
            missing = [x for x, n in ((compound, c), (target, t)) if not n]
            return {"tool": "kb.search", "args": args, "verdict": "I don’t know", "found": False,
                    "result": f"Not in the knowledge base: {', '.join(missing)}.", "rows": []}
        hits = [e for e in self.bio.out(c["id"], "INHIBITS") if e["dst"] == t["id"]]
        if hits:
            p = hits[0]["props"]
            return {"tool": "kb.search", "args": args, "verdict": "answered", "found": True, "answer": p,
                    "result": f"{c['name']} inhibits {t['name']}: IC50 {fmt_uM(p['ic50_nM'])} "
                              f"({p.get('assay', 'assay')}; {hits[0]['source']}).",
                    "rows": [[c["id"], "INHIBITS", t["id"], json.dumps(p)]]}
        return {"tool": "kb.search", "args": args, "verdict": "I don’t know", "found": False,
                "result": f"No measured activity for {c['name']} against {t['name']} in the knowledge base.",
                "rows": []}

    def bio_kg_resolve(self, compound: str, target: str) -> dict:
        c, t = self.bio.find(compound, "Compound"), self.bio.find(target, "Target")
        rows, classes = [], []
        if c:
            rows.append([c["id"], c["type"], c["name"]])
        if t:
            rows.append([t["id"], t["type"], t["name"]])
            for e in self.bio.out(t["id"], "MEMBER_OF"):
                classes.append(e["dst"])
                rows.append([e["dst"], "TargetClass", self.bio.name(e["dst"])])
        missing = [x for x, n in ((compound, c), (target, t)) if not n]
        if missing:
            summary = f"Not found in the biology KG: {', '.join(missing)}."
        elif classes:
            summary = "Both entities found; the target belongs to a class with protocol templates."
        else:
            summary = "Both entities found; the target has no class, so no protocol template applies by class."
        return {"summary": summary, "columns": ["ID", "Type", "Name"], "rows": rows,
                "compound_id": c and c["id"], "target_id": t and t["id"], "target_classes": classes}

    def bio_kg_analogs(self, compound: str, target: str, k: int = 3) -> dict:
        c, t = self.bio.find(compound, "Compound"), self.bio.find(target, "Target")
        cols = ["Compound", "Similarity", "IC50"]
        if not c or not t:
            return {"summary": "Compound or target not found.", "columns": cols, "rows": []}
        sim = {e["dst"]: e["props"].get("similarity") for e in self.bio.out(c["id"], "SIMILAR_TO")}
        sim.update({e["src"]: e["props"].get("similarity") for e in self.bio.into(c["id"], "SIMILAR_TO")})
        hits = []
        for e in self.bio.into(t["id"], "INHIBITS"):
            if e["src"] == c["id"] or "ic50_nM" not in e["props"]:
                continue
            hits.append((sim.get(e["src"]), e["src"], e["props"]["ic50_nM"]))
        hits.sort(key=lambda h: -(h[0] or 0))
        hits = hits[: int(k)]
        gene = t["props"].get("gene", t["name"])
        rows = [[f"{self.bio.name(cid)} ({cid})", f"{s:.2f}" if s is not None else "n/a", fmt_uM(ic50)]
                for s, cid, ic50 in hits]
        if hits:
            lo, hi = min(h[2] for h in hits), max(h[2] for h in hits)
            summary = f"{len(hits)} compound(s) with measured activity on {gene}: IC50 from {fmt_uM(lo)} to {fmt_uM(hi)}."
        else:
            summary = f"No compound in the KG has a measured activity on {gene}."
        return {"summary": summary, "columns": cols[:2] + [f"IC50 on {gene}"], "rows": rows,
                "ic50_nM": [h[2] for h in hits]}

    def protocol_kg_templates(self, question_type: str, target_class: str) -> dict:
        cls = self.bio.find(target_class, "TargetClass") or {"id": target_class}
        rows, templates = [], []
        for e in self.proto.into(cls["id"], "APPLICABLE_TO"):
            p = self.proto.nodes[e["src"]]
            if p["props"].get("question_type", question_type) != question_type:
                continue
            templates.append(p)
            rows.append([p["id"], p["type"], p["name"]])
            for rel, label in (("HAS_FORMAT", "Format"), ("MEASURES", "Endpoint")):
                for x in self.proto.out(p["id"], rel):
                    rows.append([x["dst"], label, self.proto.name(x["dst"])])
            for x in self.proto.out(p["id"], "USES"):
                rows.append([x["dst"], x["props"].get("role", "uses").capitalize(), self.proto.name(x["dst"])])
        n = len(templates)
        if n == 1:
            summary = f"One template fits a {question_type} question on this target class."
        elif n:
            summary = f"{n} templates fit a {question_type} question on this target class."
        else:
            summary = f"No template in the protocol KG for a {question_type} question on {cls['id']}."

        def steps(p):
            return [self.proto.name(s["dst"]) for s in
                    sorted(self.proto.out(p["id"], "HAS_STEP"), key=lambda s: s["props"].get("order", 0))]

        return {"summary": summary, "columns": ["ID", "Type", "Name"], "rows": rows,
                "templates": [{"id": p["id"], "name": p["name"], **p["props"], "steps": steps(p)} for p in templates]}

    def call(self, name: str, args: dict) -> dict:
        fn = getattr(self, name, None) if name in TOOL_NAMES else None
        if not fn:
            return {"summary": f"Unknown tool {name}.", "rows": [], "error": True}
        try:
            return fn(**args)
        except TypeError as e:
            return {"summary": f"Bad arguments for {name}: {e}", "rows": [], "error": True}

    @staticmethod
    def result_text(result: dict) -> str:
        """The result as the model sees it: the summary, the rows, and any extra detail."""
        extra = {k: v for k, v in result.items() if k not in ("summary", "result", "columns", "rows")}
        lines = [result.get("summary") or result.get("result", "")]
        if result.get("columns"):
            lines.append(" | ".join(result["columns"]))
        lines += [" | ".join(map(str, r)) for r in result["rows"]]
        if extra:
            lines.append("detail: " + json.dumps(extra))
        return "\n".join(lines)


TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "bio_kg_resolve",
        "description": "Resolve a compound and a target to their nodes in the biology knowledge graph, with the "
                       "target's class.",
        "parameters": {"type": "object", "properties": {
            "compound": {"type": "string", "description": "compound name or ChEMBL ID"},
            "target": {"type": "string", "description": "target gene symbol, name or UniProt accession"}},
            "required": ["compound", "target"]}}},
    {"type": "function", "function": {
        "name": "bio_kg_analogs",
        "description": "Compounds similar to the given one that have a measured activity on the target: use their "
                       "IC50s to pick the concentration range.",
        "parameters": {"type": "object", "properties": {
            "compound": {"type": "string"}, "target": {"type": "string"},
            "k": {"type": "integer", "description": "how many, default 3"}},
            "required": ["compound", "target"]}}},
    {"type": "function", "function": {
        "name": "protocol_kg_templates",
        "description": "Protocol templates in the protocol knowledge graph for a question type on a target class, "
                       "with their format, endpoint, controls and default parameters.",
        "parameters": {"type": "object", "properties": {
            "question_type": {"type": "string", "enum": ["potency", "cellular_activity"]},
            "target_class": {"type": "string",
                             "description": "a TargetClass node ID from bio_kg_resolve, e.g. class:tyrosine_kinase"}},
            "required": ["question_type", "target_class"]}}},
]
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SPECS}


if __name__ == "__main__":
    kb = KnowledgeBase()
    print("graphs:", kb.source)
    for name, args in [("lookup", ("imatinib", "KIT")), ("bio_kg_resolve", ("imatinib", "KIT")),
                       ("bio_kg_analogs", ("imatinib", "KIT")),
                       ("protocol_kg_templates", ("potency", "class:tyrosine_kinase"))]:
        print(f"\n{name}{args}")
        print(kb.result_text(getattr(kb, name)(*args)))
