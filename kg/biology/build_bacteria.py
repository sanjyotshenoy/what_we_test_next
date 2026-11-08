"""The bacterial MIC graph: which compounds inhibit which organisms, pathogens and gut commensals together.

`build_seed.py` builds the kinase graph and cannot build this one. Its `target_info()` returns `None` unless
the target is a human SINGLE PROTEIN, and every bacterium in ChEMBL is `target_type = ORGANISM` with no
components and no protein-class chain (*S. aureus* is `CHEMBL352`). So this is a sibling, not a flag.

**Commensal-first.** The commensal arm is small (about 1,500 usable records in all) and the pathogen arm is
enormous (160k on *S. aureus* alone), but a selectivity question needs compounds measured on *both*. So the
commensal arm is pulled whole, and the pathogen arm only for the compounds it found. Pulling pathogens first
gives a graph that is 99% rows sharing no compound with any commensal.

Three filters differ from the kinase build, deliberately:

* **Censored (`>`) values are kept.** `build_seed.py` keeps only `standard_relation = '='`. Here a
  `MIC > 128 ug/mL` on a commensal is the *finding* — evidence a compound spares it — and about a quarter of
  the records on every organism are censored. Dropping them would delete the positive class.
* **Both units are kept**, unconverted. ChEMBL reports MIC in `ug.mL-1` and in `nM` (it normalises to molar
  when it knows the molecular weight), and converting needs that weight. The edge carries value *and* unit;
  a converter belongs downstream where it can be checked.
* **`ug cm**-2` and `p.p.m.` are dropped.** The first is antimicrobial *surface coating* — a different
  experiment wearing the same `MIC` label, and 12% of *E. coli*'s records.

No year cutoff is applied here. The hold-out is a separate filter over the built graph, because baking it in
is what makes `build_seed.py` hard to reuse.

    python -m kg.biology.build_bacteria                               # all of seed/organisms.csv
    python -m kg.biology.build_bacteria --organisms CHEMBL614411 CHEMBL352
    python -m kg.biology.build_bacteria --out kg/biology/graph_bacteria
"""
import argparse
import sys
from pathlib import Path

import kg  # noqa: F401  - picks CPU or GPU mode before pandas is imported
import pandas as pd

from kg.biology.chembl_api import ChemblAPI
from kg.constants import CHEMBL_RELEASE
from kg.graph_io import write_graph

SEED = Path(__file__).with_name("seed") / "organisms.csv"
OUT = Path(__file__).with_name("graph_bacteria")
MAX_MB = 10                                   # CONTRIBUTING.md: bigger than this does not get committed

# Units that are not a broth concentration. `ug cm**-2` is a surface density (coating assays); `p.p.m.` is
# left unnormalised by ChEMBL; empty means the depositor gave none.
NON_BROTH_UNITS = {"ug cm**-2", "p.p.m.", "", None}
KEEP_RELATIONS = {"=", ">"}


def usable(activity: dict) -> bool:
    """A row we can put an edge on: a value, a broth concentration unit, a relation we can read, and a year."""
    return bool(activity.get("standard_value")
                and activity.get("standard_units") not in NON_BROTH_UNITS
                and activity.get("standard_relation") in KEEP_RELATIONS
                and activity.get("document_year"))


def read_organisms(path: Path = SEED) -> pd.DataFrame:
    """seed/organisms.csv: organism, name, role, oxygen_tolerance, gram.

    `role` and `oxygen_tolerance` are hand-curated, not from ChEMBL, which holds neither. They are what
    `wwtn.schema.PanelMember` needs and what `execution/feasibility.py` checks an experiment against, so they
    belong on the node rather than being re-derived by whoever reads the graph.
    """
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = {"organism", "name", "role", "oxygen_tolerance", "gram"} - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    return frame


def fetch(organisms: pd.DataFrame, api: ChemblAPI | None = None, log=sys.stderr) -> tuple[list[dict], dict]:
    """(activities, structures). Commensals whole, then pathogens for the compounds the commensals found."""
    api = api or ChemblAPI()
    commensals = organisms[organisms["role"] == "commensal"]
    others = organisms[organisms["role"] != "commensal"]

    rows: list[dict] = []
    for _, org in commensals.iterrows():
        found = [a for a in api.activities(org["organism"]) if usable(a)]
        rows += found
        print(f"  {org['name']:<34}{len(found):>6} usable MIC records", file=log)
    compounds = sorted({a["molecule_chembl_id"] for a in rows if a.get("molecule_chembl_id")})
    print(f"  -> {len(compounds)} distinct compounds on the commensal arm", file=log)

    for _, org in others.iterrows():
        found = [a for a in api.activities(org["organism"], compounds=compounds) if usable(a)]
        rows += found
        print(f"  {org['name']:<34}{len(found):>6} on those compounds", file=log)

    everything = sorted({a["molecule_chembl_id"] for a in rows if a.get("molecule_chembl_id")})
    return rows, api.molecules(everything)


def graph_frames(activities: list[dict], organisms: pd.DataFrame,
                 structures: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Activities + the organism seed -> (nodes, edges) in the kg/README.md format.

    Pure: no network. `fetch()` does the I/O so this half can be tested on fixtures.
    """
    structures = structures or {}
    known = set(organisms["organism"])
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for _, org in organisms.iterrows():
        nodes[org["organism"]] = {
            "id": org["organism"], "type": "Organism", "name": org["name"],
            "props": {"role": org["role"], "oxygen_tolerance": org["oxygen_tolerance"], "gram": org["gram"]},
            "source": f"{CHEMBL_RELEASE} + hand-curated traits"}

    for a in activities:
        compound, organism = a.get("molecule_chembl_id"), a.get("target_chembl_id")
        if not compound or organism not in known:
            continue
        structure = structures.get(compound, {})
        nodes.setdefault(compound, {
            "id": compound, "type": "Compound", "name": structure.get("name") or compound,
            "props": {"smiles": structure.get("smiles", "")}, "source": CHEMBL_RELEASE})
        document, assay = a.get("document_chembl_id"), a.get("assay_chembl_id")
        if document:
            nodes.setdefault(document, {
                "id": document, "type": "Document", "name": document,
                "props": {"year": a.get("document_year"), "journal": a.get("document_journal")},
                "source": CHEMBL_RELEASE})
        if assay:
            nodes.setdefault(assay, {
                "id": assay, "type": "Assay", "name": assay,
                "props": {"bao_format": a.get("bao_format"),
                          "description": (a.get("assay_description") or "")[:300]},
                "source": CHEMBL_RELEASE})
        edges.append({
            "src": compound, "rel": "INHIBITS", "dst": organism,
            "props": {"mic": float(a["standard_value"]), "unit": a["standard_units"],
                      "relation": a["standard_relation"], "assay": assay, "document": document,
                      "year": a.get("document_year")},
            "source": CHEMBL_RELEASE})

    return pd.DataFrame(list(nodes.values())), pd.DataFrame(edges)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--organisms", nargs="*", help="ChEMBL organism IDs (default: all of seed/organisms.csv)")
    parser.add_argument("--seed", type=Path, default=SEED, help=f"the organism table (default {SEED})")
    parser.add_argument("--out", type=Path, default=OUT, help=f"where to write the graph (default {OUT})")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    organisms = read_organisms(args.seed)
    if args.organisms:
        organisms = organisms[organisms["organism"].isin(args.organisms)]
        if organisms.empty:
            sys.exit(f"none of those IDs are in {args.seed}")

    print("fetching (commensals whole, then pathogens on their compounds):", file=sys.stderr)
    activities, structures = fetch(organisms)
    resolved = sum(1 for s in structures.values() if s.get("smiles"))
    print(f"structures resolved for {resolved}/{len(structures)} compounds", file=sys.stderr)

    nodes, edges = graph_frames(activities, organisms, structures)
    write_graph(args.out, nodes, edges)
    print("nodes:", nodes["type"].value_counts().to_dict())
    print("edges:", edges["rel"].value_counts().to_dict())
    size_mb = sum(p.stat().st_size for p in Path(args.out).glob("*.csv")) / 1e6
    print(f"{args.out}: {size_mb:.1f} MB")
    if size_mb > MAX_MB:
        print(f"WARNING: over {MAX_MB} MB; narrow seed/organisms.csv before committing", file=sys.stderr)


if __name__ == "__main__":
    main()
