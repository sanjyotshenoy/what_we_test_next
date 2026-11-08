"""The bacterial MIC graph, on fixtures: no ChEMBL, no network."""
import pandas as pd
import pytest

from kg.biology.build_bacteria import graph_frames, read_organisms, usable
from kg.graph_io import props_of

ORGANISMS = pd.DataFrame([
    {"organism": "CHEMBL614411", "name": "Bacteroides fragilis", "role": "commensal",
     "oxygen_tolerance": "strict anaerobe", "gram": "negative"},
    {"organism": "CHEMBL352", "name": "Staphylococcus aureus", "role": "pathogen",
     "oxygen_tolerance": "facultative", "gram": "positive"},
])


def activity(**over):
    row = {"molecule_chembl_id": "CHEMBL1753", "target_chembl_id": "CHEMBL352",
           "standard_value": "0.125", "standard_units": "ug.mL-1", "standard_relation": "=",
           "document_chembl_id": "CHEMBL1122", "document_year": 2011, "document_journal": "J Med Chem",
           "assay_chembl_id": "CHEMBL9001", "assay_description": "MIC against S. aureus",
           "bao_format": "BAO_0000218"}
    return {**row, **over}


def test_a_censored_value_is_kept_because_it_is_the_finding():
    # ">128 on a commensal" is evidence the compound spares it; build_seed.py would drop this row.
    assert usable(activity(standard_relation=">", standard_value="128"))


def test_surface_coating_and_unnormalised_units_are_dropped():
    assert not usable(activity(standard_units="ug cm**-2"))   # a coating assay, not a broth MIC
    assert not usable(activity(standard_units="p.p.m."))
    assert not usable(activity(standard_units=""))


def test_rows_without_a_value_relation_or_year_are_dropped():
    assert not usable(activity(standard_value=None))
    assert not usable(activity(standard_relation="<"))
    assert not usable(activity(document_year=None))


def test_molar_units_survive_so_the_conversion_can_happen_downstream():
    assert usable(activity(standard_units="nM", standard_value="400"))


def test_the_edge_carries_value_and_unit_rather_than_a_converted_number():
    _, edges = graph_frames([activity(standard_units="nM", standard_value="400")], ORGANISMS)
    props = props_of(edges.iloc[0]["props"])
    assert props["mic"] == 400.0 and props["unit"] == "nM"
    assert props["relation"] == "=" and props["assay"] == "CHEMBL9001"


def test_organism_nodes_carry_the_traits_chembl_does_not_have():
    nodes, _ = graph_frames([], ORGANISMS)
    fragilis = nodes[nodes["id"] == "CHEMBL614411"].iloc[0]
    props = props_of(fragilis["props"])
    assert props["role"] == "commensal"
    # execution/feasibility.py reads this; "unknown" passes the anaerobe check silently, so it must be set
    assert props["oxygen_tolerance"] == "strict anaerobe"


def test_every_node_type_appears_and_edges_point_at_organisms():
    nodes, edges = graph_frames([activity()], ORGANISMS, {"CHEMBL1753": {"name": "CLINDAMYCIN", "smiles": "CC"}})
    assert set(nodes["type"]) == {"Organism", "Compound", "Document", "Assay"}
    assert props_of(nodes[nodes["id"] == "CHEMBL1753"].iloc[0]["props"])["smiles"] == "CC"
    assert edges.iloc[0]["src"] == "CHEMBL1753" and edges.iloc[0]["dst"] == "CHEMBL352"


def test_activities_on_an_organism_outside_the_seed_are_ignored():
    _, edges = graph_frames([activity(target_chembl_id="CHEMBL999")], ORGANISMS)
    assert edges.empty


def test_read_organisms_rejects_a_table_missing_the_trait_columns(tmp_path):
    path = tmp_path / "organisms.csv"
    path.write_text("organism,name,role\nCHEMBL352,Staphylococcus aureus,pathogen\n")
    with pytest.raises(ValueError, match="oxygen_tolerance"):
        read_organisms(path)
