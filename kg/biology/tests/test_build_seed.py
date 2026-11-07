import json

import pandas as pd
import pytest

from kg.biology.build_seed import LeakageError, cap, parse_args, seed_frames
from kg.biology.targets import ProteinClass, TargetInfo
from kg.graph_io import read_frames, read_graph, write_graph

KIT = TargetInfo("CHEMBL1936", "Mast/stem cell growth factor receptor Kit", "P10721", "Homo sapiens",
                 "SINGLE PROTEIN", [ProteinClass(159, "Tyrosine protein kinase PDGFR family", 1285, 5),
                                    ProteinClass(1285, "TK protein kinase group", 1100, 4),
                                    ProteinClass(1100, "Protein Kinase", 6, 3),
                                    ProteinClass(6, "Kinase", 1, 2),
                                    ProteinClass(1, "Enzyme", 0, 1),
                                    ProteinClass(0, "Protein class", None, 0)])
EXTRA = pd.DataFrame([{"compound": "CHEMBL_NEW", "compound_name": "", "smiles": "c1ccccc1N"}])
DOCS = pd.DataFrame([{"document_chembl_id": "CHEMBL_DOC2010", "year": 2010, "pubmed_id": 1, "doi": "10.1/x",
                      "title": "An old paper", "journal": "J Med Chem"}])


def activity(molecule, value, year=2010, activity_id=1, pchembl=7.0):
    return {"activity_id": activity_id, "molecule_chembl_id": molecule, "molecule_pref_name": None,
            "canonical_smiles": "CCO", "target_chembl_id": "CHEMBL1936", "assay_chembl_id": "CHEMBL_ASSAY1",
            "assay_description": "Inhibition of KIT", "bao_format": "BAO_0000357", "assay_type": "B",
            "standard_value": float(value), "document_chembl_id": "CHEMBL_DOC2010", "document_year": year,
            "pchembl_value": pchembl}


def build(rows, extra=EXTRA):
    return seed_frames(pd.DataFrame(rows), {"CHEMBL1936": KIT}, DOCS, extra_compounds=extra)


def edge_triples(edges):
    return set(zip(edges["src"], edges["rel"], edges["dst"]))


def test_roundtrip_graph(tmp_path):
    nodes = [{"id": "P10721", "type": "Target", "name": "KIT", "props": {"chembl_id": "CHEMBL1936"},
              "source": "ChEMBL 37"}]
    edges = [{"src": "CHEMBL941", "rel": "INHIBITS", "dst": "P10721", "props": {"ic50_nM": 12.5},
              "source": "ChEMBL 37"}]
    write_graph(tmp_path, nodes, edges)
    assert read_graph(tmp_path) == (nodes, edges)
    node_frame, edge_frame = read_frames(tmp_path)
    assert list(node_frame["id"]) == ["P10721"]
    assert edge_frame.loc[0, "props"] == '{"ic50_nM": 12.5}'   # JSON text in frames (GPU-safe), dicts in rows


def test_write_graph_accepts_frames(tmp_path):
    nodes, edges = build([activity("CHEMBL_OLD", 50)])
    write_graph(tmp_path, nodes, edges)
    node_rows, edge_rows = read_graph(tmp_path)
    assert len(node_rows) == len(nodes) and len(edge_rows) == len(edges)


def test_structure_only_compound():
    nodes, edges = build([activity("CHEMBL_OLD", 50)])
    new = nodes.set_index("id").loc["CHEMBL_NEW"]
    assert json.loads(new["props"]) == {"smiles": "c1ccccc1N", "structure_only": True}
    assert not (edges["src"] == "CHEMBL_NEW").any()
    assert ("CHEMBL_OLD", "INHIBITS", "P10721") in edge_triples(edges)
    inhibits = json.loads(edges[edges["rel"] == "INHIBITS"].iloc[0]["props"])
    assert inhibits == {"ic50_nM": 50.0, "assay": "CHEMBL_ASSAY1", "document": "CHEMBL_DOC2010", "year": 2010}


def test_leakage_raises():
    with pytest.raises(LeakageError):
        build([activity("CHEMBL_OLD", 50, year=2024)])


def test_class_chain():
    _, edges = build([activity("CHEMBL_OLD", 50)])
    triples = edge_triples(edges)
    assert ("P10721", "MEMBER_OF", "chembl_class:159") in triples
    assert ("chembl_class:159", "SUBCLASS_OF", "chembl_class:1285") in triples
    assert ("chembl_class:1285", "SUBCLASS_OF", "chembl_class:1100") in triples


def test_cap():
    acts = pd.DataFrame([activity(f"m{i}", 10, year=2000 + i % 24, activity_id=i) for i in range(2500)])
    kept = cap(acts)
    assert len(kept) == 2000
    dropped_years = set(acts["document_year"]) - set(kept["document_year"])
    assert kept["document_year"].min() >= max(dropped_years, default=0)


def test_no_extra_compounds():
    nodes, _ = build([activity("CHEMBL_OLD", 50)], extra=None)
    assert "CHEMBL_NEW" not in set(nodes["id"])
    assert "CHEMBL_OLD" in set(nodes["id"])


def test_parse_targets(tmp_path):
    listed = tmp_path / "targets.txt"
    listed.write_text("# kinases\nCHEMBL1936\n\nCHEMBL4722\n")
    assert parse_args(["--targets", "CHEMBL1936", "CHEMBL2292"]).targets == ["CHEMBL1936", "CHEMBL2292"]
    assert parse_args(["--targets-file", str(listed)]).targets == ["CHEMBL1936", "CHEMBL4722"]
    assert parse_args(["--targets", "CHEMBL1936", "--targets-file", str(listed)]).targets == ["CHEMBL1936", "CHEMBL4722"]
    assert parse_args(["--targets", "CHEMBL1"]).before_year == 2024
