"""The graph tools the agent calls: the two knowledge graphs (kg/README.md CSV format) behind a handful of
functions the LLM can call, each returning rows the demo page can show.

    kb = KnowledgeBase()                      # kg/*/graph/, or agent/data/sample_kg while those are missing
    kb.lookup("CHEMBL5593141", "BTK")         # what the KB says on its own: a measurement, or "I don't know"
    kb.call("bio_kg_analogs", {...})          # one of TOOL_SPECS, by name, as the model calls it

The graphs come from `kg.query.KG` through `agent/kg_backend.py` (loaded once); each tool is one of its lookups,
shaped for the model: `bio_kg_resolve` = resolve + the class chain, `bio_kg_analogs` = the target's IC50s ranked
by RDKit Tanimoto similarity to the query compound plus the target-wide potency spread,
`protocol_kg_templates` = the protocols APPLICABLE_TO any class on the target's chain, routed by ANSWERS.

Every tool returns {"summary", "columns", "rows", ...}: `rows` are what the page tabulates, the rest is extra
detail for the model. `KnowledgeBase.result_text()` renders one for the model.
"""
import json

from .kg_backend import (KG_ROOT, REPO, SAMPLE_ROOT, GraphBackend,  # noqa: F401  - re-exported
                         fmt_uM, median, qtype)

__all__ = ["KG_ROOT", "REPO", "SAMPLE_ROOT", "KnowledgeBase", "TOOL_SPECS", "TOOL_NAMES", "fmt_uM", "qtype"]

# The demo question, answerable by experiment on the seed graph: a structure-only candidate compound (no IC50
# edge anywhere in the graph) and the one of the 19 seed kinases whose measured compounds it is closest to.
# CHEMBL5593141's nearest same-target analogs are BTK inhibitors at Tanimoto 0.53-0.60 (Morgan r2), the
# strongest same-target analog support of any candidate in kg/biology/seed/compounds.csv.
# TODO(final): confirm with Seh Na's candidate list.
DEMO_COMPOUND, DEMO_TARGET = "CHEMBL5593141", "BTK"
DEMO_QUESTION = f"Does {DEMO_COMPOUND} inhibit the {DEMO_TARGET} kinase, and how potently?"

# The seed protocols name their BAO terms in props (no node for them in the protocol graph), so the rows the
# page tabulates need a label for each. TODO(final): BAO nodes in kg/protocols would make this table unnecessary.
BAO_LABELS = {"BAO:0000357": "single protein format", "BAO:0000219": "cell-based format",
              "BAO:0000190": "IC50", "BAO:0000079": "negative control", "BAO:0000080": "positive control"}

class KnowledgeBase(GraphBackend):
    """The tools the model calls, over `agent.kg_backend.GraphBackend`: both graphs through
    `kg.query.KG`, loaded once, with the fingerprint cache that `bio_kg_analogs` needs."""

    # --- the tools ------------------------------------------------------------------------------------------

    def lookup(self, compound: str, target: str) -> dict:
        """Stage 1, before the agent runs: does the biology KG hold a measurement for this pair?"""
        args = {"compound": compound, "target": target}
        c, t = self.find_compound(compound), self.find_target(target)
        if not c or not t:
            missing = [x for x, n in ((compound, c), (target, t)) if not n]
            return {"tool": "kb.search", "args": args, "verdict": "I don’t know", "found": False,
                    "result": f"Not in the knowledge base: {', '.join(missing)}.", "rows": []}
        hits = [h for h in self.kg.neighbors(c["id"], "INHIBITS")
                if h["node"]["id"] == t["id"] and "ic50_nM" in h["props"]]
        if hits:
            values = [float(h["props"]["ic50_nM"]) for h in hits]
            p = {**hits[0]["props"], "ic50_nM": median(values)}
            how = f"median of {len(values)} measurements" if len(values) > 1 else (p.get("assay") or "assay")
            return {"tool": "kb.search", "args": args, "verdict": "answered", "found": True, "answer": p,
                    "result": f"{c['name']} inhibits {t['name']}: IC50 {fmt_uM(p['ic50_nM'])} ({how}).",
                    "rows": [[c["id"], "INHIBITS", t["id"], json.dumps(h["props"])] for h in hits[:5]]}
        return {"tool": "kb.search", "args": args, "verdict": "I don’t know", "found": False,
                "result": f"No measured activity for {c['name']} against {t['name']} in the knowledge base.",
                "rows": []}

    def bio_kg_resolve(self, compound: str, target: str) -> dict:
        c, t = self.find_compound(compound), self.find_target(target)
        rows, classes, with_templates = [], [], []
        if c:
            rows.append([c["id"], c["type"], c["name"]])
        if t:
            rows.append([t["id"], t["type"], t["name"]])
            # the whole chain, most specific first: a template may hang off any class above the target's own
            classes = [x["id"] for x in self.classes(t["id"])]
            rows += [[x, "TargetClass", self.name(x)] for x in classes]
            with_templates = self.template_classes(t["id"])
        missing = [x for x, n in ((compound, c), (target, t)) if not n]
        if missing:
            summary = f"Not found in the biology KG: {', '.join(missing)}."
        elif with_templates:
            where = ", ".join(f"{self.name(x)} ({x})" for x in with_templates)
            summary = f"Both entities found; protocol templates hang off the target's class chain at {where}."
        elif classes:
            summary = "Both entities found; no class on the target's chain has a protocol template."
        else:
            summary = "Both entities found; the target has no class, so no protocol template applies by class."
        detail = {"compound_id": c and c["id"], "target_id": t and t["id"], "target_classes": classes,
                  "template_classes": with_templates}
        if c:
            detail["compound_structure_only"] = bool(c["props"].get("structure_only"))
            detail["compound_has_smiles"] = bool(c["props"].get("smiles"))
        if t:
            detail["target_gene"] = self.gene(t)
        return {"summary": summary, "columns": ["ID", "Type", "Name"], "rows": rows, **detail}

    def bio_kg_analogs(self, compound: str, target: str, k: int = 3) -> dict:
        """The k compounds most similar to this one (Morgan r2, 2048 bits, Tanimoto) that have an IC50 on the
        same target, with the target-wide potency spread as context. The graph has no SIMILAR_TO edges: the
        similarity is computed here from the compounds' SMILES, so a structure-only candidate works too."""
        c, t = self.find_compound(compound), self.find_target(target)
        cols = ["Compound", "Similarity", "IC50"]
        if not c or not t:
            missing = [x for x, n in ((compound, c), (target, t)) if not n]
            return {"summary": f"Not found in the biology KG: {', '.join(missing)}.", "columns": cols, "rows": []}
        gene = self.gene(t)
        analogs, ranked = self.analogs(c["id"], t["id"], k)
        spread = self.potency_summary(t["id"])
        rows = [[f"{a['name']} ({a['compound']})",
                 f"{a['similarity']:.2f}" if ranked else "n/a", fmt_uM(a["ic50_nM"])] for a in analogs]
        if analogs and ranked:
            lo, hi = min(a["ic50_nM"] for a in analogs), max(a["ic50_nM"] for a in analogs)
            summary = (f"{len(analogs)} nearest analog(s) with a measured IC50 on {gene} "
                       f"(Tanimoto {analogs[-1]['similarity']:.2f}–{analogs[0]['similarity']:.2f}): "
                       f"IC50 from {fmt_uM(lo)} to {fmt_uM(hi)}.")
        elif analogs:
            summary = (f"{compound} has no usable structure, so analogs cannot be ranked by similarity: "
                       f"falling back to the {len(analogs)} most potent compounds on {gene} and its overall "
                       f"spread (n={spread['n']}, median {fmt_uM(spread['median_nM'])}).")
        else:
            summary = f"No compound in the KG has a measured IC50 on {gene}."
        return {"summary": summary, "columns": cols[:2] + [f"IC50 on {gene}"], "rows": rows,
                "ic50_nM": [a["ic50_nM"] for a in analogs],
                "similarity": [round(a["similarity"], 3) for a in analogs] if ranked else None,
                "ranked_by_similarity": ranked, "fingerprint": "Morgan r=2, 2048 bits, Tanimoto",
                "target_potency_spread_nM": spread}

    def protocol_kg_templates(self, question_type: str, target_class: str = "", target: str = "") -> dict:
        """Templates for this question type that apply to the target (or a class) or to any class above it: the
        seed graph puts a target in its most specific ChEMBL class while the templates hang off a broad one
        (Protein Kinase), and routes question types with ANSWERS edges rather than a prop."""
        wanted = qtype(question_type)
        start = (self.find_target(target) if target else None) or \
            (self.kg.resolve(target_class, type="TargetClass") or [None])[0] or \
            {"id": target_class or target, "name": target_class or target}
        matching, on_chain = self.templates(start["id"], question_type)
        details = [self.template_detail(t) for t in matching]
        rows = []
        for d in details:
            rows.append([d["id"], "Protocol", d["name"]])
            for key, label in (("bao_format", "Format"), ("bao_endpoint", "Endpoint")):
                term = d["props"].get(key)
                if term:
                    rows.append([term, label, BAO_LABELS.get(term, term)])
            rows += [[r, "Readout", r] for r in d["readout"]]
            rows += [[c["id"], BAO_LABELS.get(c["role"], str(c["role"]).capitalize()), c["name"]]
                     for c in d["controls"]]
        where = f"{start.get('name') or start['id']} ({start['id']})"
        offered = sorted({q for t in on_chain for q in t["question_types"]})
        n = len(matching)
        if n == 1:
            summary = f"One template fits a {wanted} question on {where}."
        elif n:
            summary = f"{n} templates fit a {wanted} question on {where}."
        elif on_chain:
            summary = (f"No template for a {wanted} question on {where}; the {len(on_chain)} template(s) that "
                       f"apply there answer: {', '.join(offered) or 'nothing stated'}.")
        else:
            summary = f"No template in the protocol KG applies to {where} or any class above it."
        return {"summary": summary, "columns": ["ID", "Type", "Name"], "rows": rows,
                "question_type": wanted, "via_classes": sorted({t["via_class"] for t in matching}),
                "question_types_available": offered, "templates": details}

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
                       "target's whole class chain, most specific first (e.g. a Tec-family kinase up to "
                       "chembl_class:1100, Protein Kinase, which is where protocol templates hang).",
        "parameters": {"type": "object", "properties": {
            "compound": {"type": "string", "description": "compound name or ChEMBL ID"},
            "target": {"type": "string", "description": "target gene symbol, name or UniProt accession"}},
            "required": ["compound", "target"]}}},
    {"type": "function", "function": {
        "name": "bio_kg_analogs",
        "description": "The compounds most similar to the given one (Morgan fingerprint, Tanimoto) that have a "
                       "measured IC50 on the same target: use their IC50s, and the target-wide potency spread "
                       "returned with them, to pick the concentration range.",
        "parameters": {"type": "object", "properties": {
            "compound": {"type": "string"}, "target": {"type": "string"},
            "k": {"type": "integer", "description": "how many, default 3"}},
            "required": ["compound", "target"]}}},
    {"type": "function", "function": {
        "name": "protocol_kg_templates",
        "description": "Protocol templates in the protocol knowledge graph for a question type on a target (or a "
                       "target class), with their format, endpoint, controls and default parameters.",
        "parameters": {"type": "object", "properties": {
            "question_type": {"type": "string", "enum": ["potency", "cellular_potency", "binding"]},
            "target": {"type": "string", "description": "the target (gene symbol, name or accession): its whole "
                                                        "class chain is searched"},
            "target_class": {"type": "string",
                             "description": "optional, instead of target: a TargetClass node ID from "
                                            "bio_kg_resolve, e.g. chembl_class:143"}},
            "required": ["question_type"]}}},
]
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SPECS}


if __name__ == "__main__":
    kb = KnowledgeBase()
    print("graphs:", kb.source)
    compound, target = DEMO_COMPOUND, DEMO_TARGET
    if kb.sample:                       # the hand-written sample KG has its own pair (imatinib x KIT)
        compound, target = "imatinib", "KIT"
    for name, args in [("lookup", (compound, target)), ("bio_kg_resolve", (compound, target)),
                       ("bio_kg_analogs", (compound, target)),
                       ("protocol_kg_templates", ("potency", "", target))]:
        print(f"\n{name}{args}")
        print(kb.result_text(getattr(kb, name)(*args)))
