"""The agent's view of the two knowledge graphs: a thin layer over `kg.query.KG` (kg/query.py).

`agent/tools.py` turns these lookups into the functions the LLM calls; everything graph-shaped lives here, so
the tools stay about shaping results for the model and the demo page.

    kb = GraphBackend()                     # kg/*/graph, or agent/data/sample_kg while those are missing
    kb.find_target("BTK")                   # gene symbol, name, UniProt or ChEMBL ID
    kb.classes("Q06187")                    # the class chain, most specific first
    kb.templates("Q06187", "potency")       # protocols APPLICABLE_TO any class on that chain, routed by ANSWERS
    kb.analogs("CHEMBL5593141", "Q06187")   # same-target compounds by RDKit Tanimoto similarity

The graphs are loaded once (`KG.load`), and compound fingerprints are cached per load.
"""
import re
import statistics
from pathlib import Path

from kg.graph_io import props_of  # noqa: F401  - re-exported for agent.tools
from kg.query import KG

REPO = Path(__file__).resolve().parent.parent
KG_ROOT = REPO / "kg"
SAMPLE_ROOT = REPO / "agent" / "data" / "sample_kg"   # TODO(final): drop once kg/*/graph are the real graphs

GRAPHS = ("biology", "protocols")

# The seed graph's targets carry no gene symbol (kg/README.md "known caveats": "targets carry no gene name"),
# but questions name a kinase by its gene. One line per seed target (kg/biology/seed/targets.txt).
# TODO(final): replace with gene names on the Target nodes (UniProt) once kg/biology carries them.
GENE_SYMBOLS = {
    "ACVR1": "Q04771", "ALK2": "Q04771",
    "AURKA": "O14965", "AURORA-A": "O14965",
    "CSNK1A1": "P48729", "CK1A": "P48729",
    "PRKDC": "P78527", "DNA-PK": "P78527", "DNAPK": "P78527",
    "DYRK1A": "Q13627",
    "IRAK1": "P51617",
    "LIMK1": "P53667",
    "MAPK9": "P45984", "JNK2": "P45984",
    "MAP3K7": "O43318", "TAK1": "O43318",
    "NUAK1": "O60285",
    "LATS2": "Q9NRM7",
    "SIK1": "P57059",
    "SIK3": "Q9Y2K2",
    "HASPIN": "Q8TF76", "GSG2": "Q8TF76",
    "MTOR": "P42345",
    "TLK2": "Q86UE8",
    "BTK": "Q06187",
    "MERTK": "Q12866", "MER": "Q12866",
    "AXL": "P30530", "UFO": "P30530",
}

# Question types as the protocol graph names them (`qtype:<name>` QuestionType nodes, kg/protocols/seed.py),
# plus what a model may call them instead. TODO(final): follow kg/protocols' list once the protocol DB settles.
QTYPE_ALIASES = {
    "biochemical_potency": "potency", "ic50": "potency", "inhibition": "potency", "enzyme_inhibition": "potency",
    "biochemical": "potency",
    "cellular_activity": "cellular_potency", "cellular": "cellular_potency", "cell_viability": "cellular_potency",
    "cell_potency": "cellular_potency", "viability": "cellular_potency",
    "affinity": "binding", "binding_affinity": "binding", "kd": "binding",
}

FP_RADIUS, FP_BITS = 2, 2048   # Morgan radius 2, 2048 bits: the leakage check in DISCUSSIONS.md uses the same


def fmt_uM(nM: float) -> str:
    uM = nM / 1000
    return f"{uM:g} µM" if uM >= 1 else f"{nM:.3g} nM"


def qtype(text: str | None) -> str:
    """A question type in canonical form: `qtype:Cellular Activity` -> `cellular_potency`."""
    t = re.sub(r"[\s\-]+", "_", str(text or "").strip().lower())
    if t.startswith("qtype:"):
        t = t.split(":", 1)[1]
    return QTYPE_ALIASES.get(t, t)


def median(values) -> float:
    return float(statistics.median(list(values)))


class GraphBackend:
    """Both graphs behind the lookups the agent needs. `sample` says which graphs were found."""

    def __init__(self, root: Path | None = None):
        root = Path(root) if root else KG_ROOT
        folders = [root / g / "graph" for g in GRAPHS]
        self.sample = not all((f / "nodes.csv").exists() for f in folders)
        if self.sample:
            folders = [SAMPLE_ROOT / g for g in GRAPHS]
        self.folders = folders
        self.kg = KG.load(folders)
        self._fps: dict[str, object] = {}        # compound ID -> fingerprint or None, cached per load
        self._target_nodes: list[dict] | None = None

    @property
    def source(self) -> str:
        return "agent/data/sample_kg (hand-written stand-in)" if self.sample else "kg/*/graph"

    # --- nodes -----------------------------------------------------------------------------------------------

    def node(self, id: str) -> dict | None:
        return self.kg.node(id)

    def name(self, id: str) -> str:
        n = self.kg.node(id)
        name = n.get("name") if n else None
        return name if isinstance(name, str) and name else id

    def targets(self) -> list[dict]:
        if self._target_nodes is None:
            ids = self.kg.nodes_df.loc[self.kg.nodes_df["type"] == "Target", "id"].to_list()
            self._target_nodes = [n for n in (self.kg.node(i) for i in ids) if n]
        return self._target_nodes

    def gene(self, target: dict) -> str:
        """A short label for a target: its `gene` prop, else a symbol from GENE_SYMBOLS, else its name."""
        g = target["props"].get("gene")
        if not g:
            g = next((s for s, u in GENE_SYMBOLS.items() if u == target["id"]), None)
        return g or target.get("name") or target["id"]

    def find_compound(self, text: str) -> dict | None:
        found = self.kg.resolve(str(text or ""), type="Compound")
        return found[0] if found else None

    def find_target(self, text: str) -> dict | None:
        """A target by `gene` prop, then the GENE_SYMBOLS table, then `KG.resolve` (ID, name, ChEMBL ID)."""
        t = str(text or "").strip()
        if not t:
            return None
        for n in self.targets():
            if str(n["props"].get("gene", "")).upper() == t.upper():
                return n
        mapped = GENE_SYMBOLS.get(t.upper())
        if mapped and self.kg.node(mapped):
            return self.kg.node(mapped)
        found = self.kg.resolve(t, type="Target")
        return found[0] if found else None

    def mentions(self, text: str) -> tuple[str | None, str | None]:
        """The compound and target a question text names, matched against the graph with no LLM: ChEMBL IDs,
        then gene symbols and node names that appear as whole words."""
        low = str(text or "").lower()
        words = set(re.findall(r"[a-z0-9][a-z0-9\-]*", low))
        compound = target = None
        for raw in re.findall(r"chembl\d+", low):
            n = self.kg.node(raw.upper())
            if n and n["type"] == "Compound":
                compound = compound or n["id"]
            else:
                hit = self.kg.resolve(raw.upper(), type="Target")   # a target's own ChEMBL ID
                target = target or (hit[0]["id"] if hit else None)
        if not compound:
            frame = self.kg.nodes_df[self.kg.nodes_df["type"] == "Compound"]
            for id_, name in zip(frame["id"].to_list(), frame["name"].astype(str).to_list()):
                n = name.lower()
                if len(n) >= 4 and re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", low):
                    compound = id_
                    break
        if not target:
            for n in self.targets():
                symbols = {str(n["props"].get("gene", "")).lower()}
                symbols |= {s.lower() for s, u in GENE_SYMBOLS.items() if u == n["id"]}
                if (words & (symbols - {""})) or str(n.get("name", "")).lower() in low:
                    target = n["id"]
                    break
        return compound, target

    # --- chemistry -------------------------------------------------------------------------------------------

    def _generator(self):
        if not hasattr(self, "_fpgen"):
            from rdkit import RDLogger
            from rdkit.Chem import rdFingerprintGenerator
            RDLogger.DisableLog("rdApp.*")   # a bad SMILES in the graph is a missing fingerprint, not a warning
            self._fpgen = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)
        return self._fpgen

    def fingerprint(self, compound_id: str, smiles: str | None = None):
        """The compound's Morgan fingerprint, or None when it has no usable SMILES. Cached per load."""
        if compound_id in self._fps:
            return self._fps[compound_id]
        from rdkit import Chem
        if smiles is None:
            node = self.kg.node(compound_id)
            smiles = (node or {}).get("props", {}).get("smiles") or ""
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        self._fps[compound_id] = self._generator().GetFingerprint(mol) if mol is not None else None
        return self._fps[compound_id]

    def activities(self, target_id: str, limit: int = 100000) -> list[dict]:
        """Every IC50 on the target, most potent first (`KG.activities`)."""
        return self.kg.activities(target_id, limit=limit)

    def potency_summary(self, target_id: str) -> dict:
        return self.kg.potency_summary(target_id)

    def analogs(self, compound_id: str, target_id: str, k: int = 3) -> tuple[list[dict], bool]:
        """The k compounds most similar to `compound_id` that have an IC50 on `target_id`, by Tanimoto on Morgan
        fingerprints. Returns (analogs, ranked): `ranked` is False when the query compound has no usable SMILES,
        and the list is then the most potent compounds on the target, with no similarity."""
        from rdkit import DataStructs
        per_compound: dict[str, dict] = {}
        for a in self.activities(target_id):
            if a["compound"] == compound_id:
                continue
            seen = per_compound.setdefault(a["compound"], {"compound": a["compound"], "name": a["name"],
                                                           "smiles": a["smiles"], "ic50_nM": [], "assay": a["assay"],
                                                           "document": a["document"], "year": a["year"]})
            seen["ic50_nM"].append(float(a["ic50_nM"]))
        candidates = list(per_compound.values())
        for c in candidates:
            values = c.pop("ic50_nM")
            c["ic50_nM"], c["n_measurements"] = median(values), len(values)
        query = self.fingerprint(compound_id)
        if query is None:
            candidates.sort(key=lambda c: (c["ic50_nM"], c["compound"]))
            return candidates[: int(k)], False
        with_fp = [(c, self.fingerprint(c["compound"], c["smiles"])) for c in candidates]
        with_fp = [(c, fp) for c, fp in with_fp if fp is not None]
        if not with_fp:
            candidates.sort(key=lambda c: (c["ic50_nM"], c["compound"]))
            return candidates[: int(k)], False
        sims = DataStructs.BulkTanimotoSimilarity(query, [fp for _, fp in with_fp])
        for (c, _), s in zip(with_fp, sims):
            c["similarity"] = float(s)
        ranked = sorted((c for c, _ in with_fp), key=lambda c: (-c["similarity"], c["ic50_nM"], c["compound"]))
        return ranked[: int(k)], True

    # --- classes and templates -------------------------------------------------------------------------------

    def classes(self, target_id: str) -> list[dict]:
        """The target's TargetClass chain, most specific first (`KG.classes`, up MEMBER_OF then SUBCLASS_OF)."""
        return self.kg.classes(target_id)

    def template_classes(self, target_id: str) -> list[str]:
        """Classes on the chain that actually have a protocol APPLICABLE_TO them."""
        return [c["id"] for c in self.classes(target_id)
                if self.kg.neighbors(c["id"], "APPLICABLE_TO", direction="in")]

    def templates(self, target_id: str, question_type: str | None = None) -> tuple[list[dict], list[dict]]:
        """(matching, all_on_chain): every protocol applicable to any class on the target's chain
        (`KG.templates`), and those whose ANSWERS edges cover `question_type`. A template with no ANSWERS edge
        answers anything; a question type that matches nothing gives an empty `matching`, never everything."""
        found = self.kg.templates(target_id)
        for t in found:
            t["question_types"] = sorted({qtype(a) for a in t.get("answers") or []})
        wanted = qtype(question_type) if question_type else ""
        if not wanted:
            return list(found), found
        matching = [t for t in found if not t["question_types"] or wanted in t["question_types"]]
        return matching, found

    def question_types(self, target_id: str) -> list[str]:
        """The question types the target's applicable templates can answer."""
        _, found = self.templates(target_id)
        return sorted({q for t in found for q in t["question_types"]})

    def template_detail(self, template: dict) -> dict:
        """One template with the extras the model and the page want: steps in order, controls, parameters."""
        pid = template["id"]
        steps = [(s["props"].get("order", 0), s["node"].get("name") or s["node"]["id"])
                 for s in self.kg.neighbors(pid, "HAS_STEP")]
        node = self.kg.node(pid) or {"props": {}}
        controls = [{"id": u["node"]["id"], "name": u["node"].get("name") or u["node"]["id"],
                     "role": u["node"].get("props", {}).get("bao") or u["props"].get("role", "uses")}
                    for u in self.kg.neighbors(pid, "USES")]
        params = {name: props for name, props in template.get("params", {}).items()}
        return {"id": pid, "name": template.get("name") or pid, "purpose": template.get("purpose"),
                "via_class": template.get("via_class"), "question_types": template.get("question_types", []),
                "readout": template.get("readout", []), "params": params, "controls": controls,
                "steps": [s for _, s in sorted(steps, key=lambda s: s[0])],
                "props": {k: v for k, v in node.get("props", {}).items() if k != "purpose"}}
