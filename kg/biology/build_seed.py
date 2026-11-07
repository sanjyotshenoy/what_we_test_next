"""Seed biology graph: ChEMBL data published before a cutoff year, around a list of targets.

TODO(final): seed graph for testing; replace with the kg/biology owner's graph.

    python -m kg.biology.build_seed --targets CHEMBL1936 CHEMBL4722          # writes kg/biology/graph/
    python -m kg.biology.build_seed --targets-file targets.txt --compounds new_compounds.csv
    WWTN_GPU=1 python -m kg.biology.build_seed --targets ...                 # the same on the GPU (kg/backend.py)

Reads the local ChEMBL 37 SQLite dump (kg/biology/chembl_db.py says where to get it). For every target: its IC50s
from documents published before --before-year (default CUTOFF_YEAR; capped at CAP_PER_TARGET), the compounds,
assays and papers (Document nodes) behind them, and ChEMBL's protein-class chain up to the root. --compounds adds
compounds with their structure only (CSV columns: compound, compound_name, smiles), e.g. molecules a question asks
about, so a query can find them without the graph knowing their activity. Nothing from the cutoff year on may
enter: seed_frames raises LeakageError instead. Tables are built column-wise with pandas, so the same code scales
to much larger graphs.
"""
import argparse
import sys
from pathlib import Path

import kg  # noqa: F401  - picks CPU or GPU mode before pandas is imported
import pandas as pd

from kg.backend import mode
from kg.biology.chembl_db import ChemblDB
from kg.biology.targets import TargetInfo
from kg.constants import CAP_PER_TARGET, CHEMBL_RELEASE, CUTOFF_YEAR
from kg.graph_io import EDGE_COLUMNS, NODE_COLUMNS, props_text, write_graph

OUT = Path("kg/biology/graph")
STRUCTURE_ONLY_SOURCE = "structure only (no activities)"
MAX_MB = 10


class LeakageError(Exception):
    """Data from a held-out year (CUTOFF_YEAR or later, or of unknown year) was about to enter the graph."""


def cap(acts: pd.DataFrame, n: int = CAP_PER_TARGET) -> pd.DataFrame:
    """Per target, keep the n most recent activities, rows with a pChEMBL value first; ties by activity_id."""
    ranked = acts.assign(_no_pchembl=acts["pchembl_value"].isna()).sort_values(
        ["target_chembl_id", "document_year", "_no_pchembl", "activity_id"], ascending=[True, False, True, True])
    return ranked.groupby("target_chembl_id", sort=False).head(n).drop(columns="_no_pchembl")


def _check_years(years: pd.Series, what: str, before_year: int) -> None:
    bad = years.isna() | (pd.to_numeric(years, errors="coerce") >= before_year)
    if bad.any():
        raise LeakageError(f"{int(bad.sum())} {what} have a year >= {before_year} or no year; only data before "
                           f"{before_year} may enter the graph")


def _nodes(ids, type: str, names, props, source=CHEMBL_RELEASE) -> pd.DataFrame:
    ids = list(ids)
    return pd.DataFrame({"id": ids, "type": type, "name": list(names), "props": [props_text(p) for p in props],
                         "source": source})


def _edges(src, rel: str, dst, props=None) -> pd.DataFrame:
    src = list(src)
    return pd.DataFrame({"src": src, "rel": rel, "dst": list(dst),
                         "props": [props_text(p) for p in props] if props is not None else ["{}" for _ in src],
                         "source": CHEMBL_RELEASE})


def seed_frames(acts: pd.DataFrame, targets: dict[str, TargetInfo], docs: pd.DataFrame,
                extra_compounds: pd.DataFrame | None = None,
                before_year: int = CUTOFF_YEAR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`acts`: activity rows for all targets (ChemblDB.activities); `targets` keyed by ChEMBL target ID;
    `docs`: ChemblDB.documents rows; `extra_compounds`: optional structure-only compounds (compound,
    compound_name, smiles). Returns (nodes, edges) frames in the kg/README.md columns."""
    acts = cap(acts)
    _check_years(acts["document_year"], "activities", before_year)
    uniprot = {t: info.uniprot for t, info in targets.items()}
    node_parts, edge_parts = [], []

    # Targets and their class chains (a handful of rows: plain Python is clearest).
    for info in targets.values():
        node_parts.append(_nodes([info.uniprot], "Target", [info.pref_name], [{"chembl_id": info.target_chembl_id}]))
        classes = info.classes
        node_parts.append(_nodes([f"chembl_class:{c.id}" for c in classes], "TargetClass", [c.name for c in classes],
                                 [{"level": c.level} for c in classes]))
        if classes:
            edge_parts.append(_edges([info.uniprot], "MEMBER_OF", [f"chembl_class:{classes[0].id}"]))
            edge_parts.append(_edges([f"chembl_class:{c.id}" for c in classes[:-1]], "SUBCLASS_OF",
                                     [f"chembl_class:{c.id}" for c in classes[1:]]))

    # Compounds, assays and activities, column-wise.
    compounds = acts.drop_duplicates("molecule_chembl_id")
    node_parts.append(_nodes(compounds["molecule_chembl_id"], "Compound",
                             compounds["molecule_pref_name"].fillna(compounds["molecule_chembl_id"]),
                             ({"smiles": s or ""} for s in compounds["canonical_smiles"].fillna(""))))
    assays = acts.drop_duplicates("assay_chembl_id")
    node_parts.append(_nodes(assays["assay_chembl_id"], "Assay", assays["assay_chembl_id"],
                             ({"description": d, "bao_format": b, "assay_type": t} for d, b, t in
                              zip(assays["assay_description"].fillna(""), assays["bao_format"].fillna(""),
                                  assays["assay_type"].fillna("")))))
    edge_parts.append(_edges(acts["molecule_chembl_id"], "INHIBITS", acts["target_chembl_id"].map(uniprot),
                             ({"ic50_nM": float(v), "assay": a, "document": d, "year": int(y)} for v, a, d, y in
                              zip(acts["standard_value"], acts["assay_chembl_id"], acts["document_chembl_id"],
                                  acts["document_year"]))))
    from_doc = acts.drop_duplicates(["assay_chembl_id", "document_chembl_id"])
    edge_parts.append(_edges(from_doc["assay_chembl_id"], "FROM_DOC", from_doc["document_chembl_id"]))

    # Papers behind the activities.
    used = docs[docs["document_chembl_id"].isin(set(acts["document_chembl_id"]))]
    _check_years(used["year"], "documents", before_year)
    node_parts.append(_nodes(used["document_chembl_id"], "Document",
                             used["title"].fillna(used["document_chembl_id"]),
                             ({"year": int(y), "pmid": None if pd.isna(p) else int(p), "doi": d, "title": t,
                               "journal": j} for y, p, d, t, j in
                              zip(used["year"], used["pubmed_id"], used["doi"], used["title"], used["journal"]))))

    # Extra compounds: structure only, unless the graph already holds them through activities (then the existing
    # node, with its activities, is kept).
    if extra_compounds is not None and len(extra_compounds):
        known = set(pd.concat(node_parts)["id"])
        new = extra_compounds[~extra_compounds["compound"].isin(known)].drop_duplicates("compound")
        names = new["compound_name"].fillna("") if "compound_name" in new else pd.Series("", index=new.index)
        node_parts.append(_nodes(new["compound"], "Compound", names.replace("", pd.NA).fillna(new["compound"]),
                                 ({"smiles": s or "", "structure_only": True} for s in new["smiles"].fillna("")),
                                 STRUCTURE_ONLY_SOURCE))

    nodes = pd.concat(node_parts, ignore_index=True)[NODE_COLUMNS].drop_duplicates("id")
    edges = pd.concat(edge_parts, ignore_index=True)[EDGE_COLUMNS]
    return nodes, edges


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the seed biology graph from the local ChEMBL dump.")
    parser.add_argument("--targets", nargs="+", default=[], help="ChEMBL target IDs, e.g. CHEMBL1936")
    parser.add_argument("--targets-file", type=Path, help="one ChEMBL target ID per line (# comments allowed)")
    parser.add_argument("--compounds", type=Path, help="CSV of structure-only compounds: compound,compound_name,smiles")
    parser.add_argument("--before-year", type=int, default=CUTOFF_YEAR, help="only documents before this year")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    targets = list(args.targets)
    if args.targets_file:
        for line in args.targets_file.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                targets.append(line)
    args.targets = list(dict.fromkeys(targets))
    if not args.targets:
        parser.error("give --targets or --targets-file")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    db = ChemblDB()
    targets = {t: db.target_info(t) for t in args.targets}
    missing = [t for t, info in targets.items() if info is None]
    if missing:
        sys.exit(f"not human single-protein targets in ChEMBL: {', '.join(missing)}")
    acts = pd.concat([db.activities(t, before_year=args.before_year, limit=CAP_PER_TARGET) for t in targets],
                     ignore_index=True)
    print(acts.groupby("target_chembl_id").size().to_string(), file=sys.stderr)
    docs = db.documents(sorted(set(acts["document_chembl_id"])))
    extra = pd.read_csv(args.compounds, dtype=str, keep_default_na=False) if args.compounds else None

    nodes, edges = seed_frames(acts, targets, docs, extra_compounds=extra, before_year=args.before_year)
    write_graph(args.out, nodes, edges)
    print(f"[{mode()}] nodes:", nodes["type"].value_counts().to_dict())
    print(f"[{mode()}] edges:", edges["rel"].value_counts().to_dict())
    size_mb = sum(p.stat().st_size for p in Path(args.out).glob("*.csv")) / 1e6
    print(f"{args.out}: {size_mb:.1f} MB")
    if size_mb > MAX_MB:
        print(f"WARNING: over {MAX_MB} MB; lower CAP_PER_TARGET before committing")


if __name__ == "__main__":
    main()
