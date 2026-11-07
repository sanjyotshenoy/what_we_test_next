"""A tiny KG in the kg/README.md format for the agent's tools, written to a tmp folder.

Two targets with a class chain (a narrow family under Protein Kinase, as in the seed graph, so a template that
hangs off the broad class is only found by walking SUBCLASS_OF), a non-kinase class with its own template,
protocols with ANSWERS and APPLICABLE_TO edges, and a handful of compounds with SMILES and IC50s.
"""
import pytest

from kg.graph_io import write_graph

# Real SMILES, short enough to read: the first three are nitrogen heterocycles that share a scaffold, so
# QUERY is closest to ANALOG_A and ANALOG_B and further from the aspirin-like outlier.
QUERY = "c1ccc2c(c1)[nH]c1ccncc12"            # structure-only candidate: no IC50 edge anywhere
ANALOG_A = "Cc1ccc2c(c1)[nH]c1ccncc12"
ANALOG_B = "Clc1ccc2c(c1)[nH]c1ccncc12"
OUTLIER = "CC(=O)Oc1ccccc1C(=O)O"             # aspirin: nothing like the others


def _nodes():
    n = lambda id, type, name, **props: {"id": id, "type": type, "name": name, "props": props,  # noqa: E731
                                         "source": "test fixture"}
    return [
        # targets and their class chain: KIN1 is MEMBER_OF the narrow family, which is SUBCLASS_OF Protein Kinase
        n("P00001", "Target", "Test kinase one", chembl_id="CHEMBL0001"),
        n("P00002", "Target", "Test kinase two", chembl_id="CHEMBL0002"),
        n("P00003", "Target", "Test protease", chembl_id="CHEMBL0003"),
        n("class:family", "TargetClass", "Test kinase family", level=5),
        n("class:kinase", "TargetClass", "Protein Kinase", level=3),
        n("class:protease", "TargetClass", "Protease", level=3),
        # compounds: the query compound carries a structure only, the analogs have IC50s
        n("CAND1", "Compound", "CAND1", smiles=QUERY, structure_only=True),
        n("CAND2", "Compound", "CAND2", structure_only=True),            # no SMILES at all
        n("CMP_A", "Compound", "analog-a", smiles=ANALOG_A),
        n("CMP_B", "Compound", "analog-b", smiles=ANALOG_B),
        n("CMP_OUT", "Compound", "outlier", smiles=OUTLIER),
        # protocols: one per question type, on the broad kinase class; one on the protease class
        n("proto:biochem", "Protocol", "Biochemical kinase inhibition",
          purpose="Measure IC50 on a purified kinase.", bao_format="BAO:0000357", bao_endpoint="BAO:0000190"),
        n("proto:cells", "Protocol", "Cell viability", purpose="Measure the effect on cultured cells.",
          bao_format="BAO:0000219"),
        n("proto:protease", "Protocol", "Protease inhibition", purpose="Measure IC50 on a protease."),
        n("qtype:potency", "QuestionType", "potency"),
        n("qtype:cellular_potency", "QuestionType", "cellular_potency"),
        n("readout:lum", "Readout", "luminescence"),
        n("reagent:dmso", "Reagent", "DMSO vehicle", bao="BAO:0000079"),
        n("proto:biochem/param/top_concentration", "Parameter", "top_concentration", value=10, unit="uM"),
        n("proto:biochem/step1", "Step", "Dilute the compound.", verb="serial_dilute", order=1),
        n("proto:biochem/step2", "Step", "Read luminescence.", verb="read", order=2),
    ]


def _edges():
    e = lambda src, rel, dst, **props: {"src": src, "rel": rel, "dst": dst, "props": props,  # noqa: E731
                                        "source": "test fixture"}
    return [
        e("P00001", "MEMBER_OF", "class:family"),
        e("class:family", "SUBCLASS_OF", "class:kinase"),
        e("P00002", "MEMBER_OF", "class:kinase"),
        e("P00003", "MEMBER_OF", "class:protease"),
        # IC50s on target one: two near analogs and one structurally unrelated compound
        e("CMP_A", "INHIBITS", "P00001", ic50_nM=100, assay="A1", document="D1", year=2020),
        e("CMP_A", "INHIBITS", "P00001", ic50_nM=300, assay="A2", document="D2", year=2021),
        e("CMP_B", "INHIBITS", "P00001", ic50_nM=50, assay="A1", document="D1", year=2020),
        e("CMP_OUT", "INHIBITS", "P00001", ic50_nM=5, assay="A3", document="D3", year=2019),
        # an IC50 on target two, so lookup() can find a measured pair
        e("CMP_A", "INHIBITS", "P00002", ic50_nM=2000, assay="A4", document="D4", year=2022),
        # the templates: both kinase ones on the BROAD class, routed by ANSWERS
        e("proto:biochem", "APPLICABLE_TO", "class:kinase"),
        e("proto:biochem", "ANSWERS", "qtype:potency"),
        e("proto:biochem", "MEASURES", "readout:lum"),
        e("proto:biochem", "USES", "reagent:dmso"),
        e("proto:biochem", "HAS_PARAM", "proto:biochem/param/top_concentration"),
        e("proto:biochem", "HAS_STEP", "proto:biochem/step1", order=1),
        e("proto:biochem", "HAS_STEP", "proto:biochem/step2", order=2),
        e("proto:cells", "APPLICABLE_TO", "class:kinase"),
        e("proto:cells", "ANSWERS", "qtype:cellular_potency"),
        e("proto:protease", "APPLICABLE_TO", "class:protease"),
        e("proto:protease", "ANSWERS", "qtype:potency"),
    ]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No test reaches the network: agent/compounds.py honours WWTN_OFFLINE, and the ChEMBL API tests stub
    `fetch` instead. A test that wants the stubbed API sets its own cache folder."""
    monkeypatch.setenv("WWTN_OFFLINE", "1")


@pytest.fixture(scope="session")
def fixture_kg(tmp_path_factory):
    """A root holding biology/graph and protocols/graph, as `KnowledgeBase(root)` expects."""
    root = tmp_path_factory.mktemp("fixture_kg")
    nodes, edges = _nodes(), _edges()
    bio_types = {"Target", "TargetClass", "Compound"}
    write_graph(root / "biology" / "graph", [n for n in nodes if n["type"] in bio_types],
                [x for x in edges if x["rel"] in ("MEMBER_OF", "SUBCLASS_OF", "INHIBITS")])
    write_graph(root / "protocols" / "graph", [n for n in nodes if n["type"] not in bio_types],
                [x for x in edges if x["rel"] not in ("MEMBER_OF", "SUBCLASS_OF", "INHIBITS")])
    return root


@pytest.fixture()
def kb(fixture_kg):
    from agent.tools import KnowledgeBase
    return KnowledgeBase(fixture_kg)
