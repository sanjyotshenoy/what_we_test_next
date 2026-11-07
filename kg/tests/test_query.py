import pytest

from kg.graph_io import write_graph
from kg.query import KG

SRC = "test"


def n(id, type, name, **props):
    return {"id": id, "type": type, "name": name, "props": props, "source": SRC}


def e(src, rel, dst, **props):
    return {"src": src, "rel": rel, "dst": dst, "props": props, "source": SRC}


@pytest.fixture
def kg(tmp_path):
    bio = [
        n("P10721", "Target", "Mast/stem cell growth factor receptor Kit", chembl_id="CHEMBL1936"),
        n("chembl_class:159", "TargetClass", "Tyrosine protein kinase PDGFR family"),
        n("chembl_class:1100", "TargetClass", "Protein Kinase"),
        n("CHEMBL941", "Compound", "IMATINIB", smiles="CCO"),
        n("CHEMBL2", "Compound", "CHEMBL2", smiles="CCN"),
        n("CHEMBL3", "Compound", "CHEMBL3", smiles="CCC"),
        n("CHEMBL_DOC", "Document", "A paper", year=2010),
    ]
    bio_edges = [
        e("P10721", "MEMBER_OF", "chembl_class:159"),
        e("chembl_class:159", "SUBCLASS_OF", "chembl_class:1100"),
        e("CHEMBL3", "INHIBITS", "P10721", ic50_nM=500.0, assay="A1", document="CHEMBL_DOC", year=2010),
        e("CHEMBL941", "INHIBITS", "P10721", ic50_nM=5.0, assay="A1", document="CHEMBL_DOC", year=2010),
        e("CHEMBL2", "INHIBITS", "P10721", ic50_nM=50.0, assay="A1", document="CHEMBL_DOC", year=2010),
    ]
    proto = [
        n("proto:kinase_biochem_lum", "Protocol", "Biochemical kinase inhibition", purpose="potency"),
        n("proto:kinase_biochem_lum/param/dilution_factor", "Parameter", "dilution_factor", value=3, unit="fold"),
        n("readout:lum", "Readout", "luminescence"),
        n("qtype:potency", "QuestionType", "potency"),
    ]
    proto_edges = [
        e("proto:kinase_biochem_lum", "APPLICABLE_TO", "chembl_class:1100"),
        e("proto:kinase_biochem_lum", "HAS_PARAM", "proto:kinase_biochem_lum/param/dilution_factor"),
        e("proto:kinase_biochem_lum", "MEASURES", "readout:lum"),
        e("proto:kinase_biochem_lum", "ANSWERS", "qtype:potency"),
    ]
    write_graph(tmp_path / "bio", bio, bio_edges)
    write_graph(tmp_path / "proto", proto, proto_edges)
    return KG.load([tmp_path / "bio", tmp_path / "proto"])


def test_resolve_id_name_chembl(kg):
    assert kg.resolve("P10721")[0]["id"] == "P10721"
    assert kg.resolve("CHEMBL1936")[0]["id"] == "P10721"
    assert kg.resolve("growth factor receptor kit")[0]["id"] == "P10721"
    assert kg.resolve("imatinib")[0]["id"] == "CHEMBL941"


def test_classes_order(kg):
    assert [c["id"] for c in kg.classes("P10721")] == ["chembl_class:159", "chembl_class:1100"]


def test_activities_sorted(kg):
    assert [a["ic50_nM"] for a in kg.activities("P10721")] == [5.0, 50.0, 500.0]


def test_potency_summary(kg):
    assert kg.potency_summary("P10721") == {"n": 3, "min_nM": 5.0, "median_nM": 50.0, "max_nM": 500.0}


def test_templates_via_class(kg):
    found = kg.templates("P10721")
    assert [t["id"] for t in found] == ["proto:kinase_biochem_lum"]
    assert found[0]["params"]["dilution_factor"]["value"] == 3


def test_frames_and_graph(kg):
    import networkx as nx
    import pandas as pd
    assert isinstance(kg.nodes_df, pd.DataFrame) and isinstance(kg.edges_df, pd.DataFrame)
    assert isinstance(kg.graph, nx.MultiDiGraph)
    assert kg.graph.number_of_edges() == len(kg.edges_df) == 9
    assert kg.graph.has_edge("CHEMBL941", "P10721")


def test_from_lists_matches_load(kg):
    rebuilt = KG(kg.nodes_df.to_dict("records"), kg.edges_df.to_dict("records"))
    assert rebuilt.activities("P10721") == kg.activities("P10721")


def test_unknown_id(kg):
    assert kg.node("nope") is None
    assert kg.templates("nope") == []
