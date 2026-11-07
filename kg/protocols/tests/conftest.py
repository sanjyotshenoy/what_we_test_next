"""Shared fixtures for the protocol-graph tests: the built graph, and both graphs behind a KG."""
import pytest

from kg.graph_io import write_graph
from kg.protocols.build_db import build
from kg.query import KG

KINASE_CLASS = "chembl_class:1100"


@pytest.fixture(scope="module")
def graph():
    nodes, edges = build()
    return {n["id"]: n for n in nodes}, edges


@pytest.fixture(scope="module")
def kg(tmp_path_factory, graph):
    """Both graphs: the real protocol graph plus a two-target stand-in biology graph."""
    nodes, edges = graph
    folder = tmp_path_factory.mktemp("kg")
    bio_nodes = [
        {"id": "Q13627", "type": "Target", "name": "DYRK1A", "props": {}, "source": "test"},
        {"id": "P00533", "type": "Target", "name": "a protease, for the test", "props": {}, "source": "test"},
        {"id": KINASE_CLASS, "type": "TargetClass", "name": "Protein Kinase", "props": {}, "source": "test"},
        {"id": "chembl_class:1028", "type": "TargetClass", "name": "Protease", "props": {}, "source": "test"},
    ]
    bio_edges = [
        {"src": "Q13627", "rel": "MEMBER_OF", "dst": KINASE_CLASS, "props": {}, "source": "test"},
        {"src": "P00533", "rel": "MEMBER_OF", "dst": "chembl_class:1028", "props": {}, "source": "test"},
    ]
    write_graph(folder / "bio", bio_nodes, bio_edges)
    write_graph(folder / "proto", list(nodes.values()), edges)
    return KG.load([folder / "bio", folder / "proto"])
