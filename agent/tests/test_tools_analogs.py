"""Analogs by RDKit similarity on the same target (problem 3): the graph has no SIMILAR_TO edges, so the tool
computes Morgan/Tanimoto similarity between the query compound and the compounds with an IC50 on that target."""
import pytest

from agent.kg_backend import FP_BITS, FP_RADIUS


def test_ranked_by_similarity_not_by_potency(kb):
    r = kb.bio_kg_analogs("CAND1", "P00001", k=3)
    assert r["ranked_by_similarity"] is True
    ids = [row[0].split("(")[-1].rstrip(")") for row in r["rows"]]
    assert set(ids[:2]) == {"CMP_A", "CMP_B"}     # the two near analogs come first
    assert ids[-1] == "CMP_OUT"                   # the most potent compound (5 nM) ranks last: it is unrelated
    assert r["similarity"][0] > r["similarity"][-1]
    assert r["similarity"][-1] < 0.2
    assert r["fingerprint"] == f"Morgan r={FP_RADIUS}, {FP_BITS} bits, Tanimoto"


def test_k_limits_the_rows(kb):
    assert len(kb.bio_kg_analogs("CAND1", "P00001", k=1)["rows"]) == 1
    assert len(kb.bio_kg_analogs("CAND1", "P00001", k=2)["rows"]) == 2


def test_only_same_target_compounds_are_offered(kb):
    """CMP_A has an IC50 on both targets; on target two it is the only measured compound."""
    r = kb.bio_kg_analogs("CAND1", "P00002", k=5)
    assert [row[0] for row in r["rows"]] == ["analog-a (CMP_A)"]
    assert r["ic50_nM"] == [2000.0]


def test_repeated_measurements_are_summarised_as_a_median(kb):
    r = kb.bio_kg_analogs("CAND1", "P00001", k=3)
    by_id = {row[0]: row[2] for row in r["rows"]}
    assert by_id["analog-a (CMP_A)"] == "200 nM"   # median of 100 and 300 nM


def test_target_wide_spread_comes_with_it(kb):
    spread = kb.bio_kg_analogs("CAND1", "P00001")["target_potency_spread_nM"]
    assert spread == {"n": 4, "min_nM": 5.0, "median_nM": 75.0, "max_nM": 300.0}


def test_structure_only_query_compound_is_fine(kb):
    """CAND1 has no IC50 edge of its own, only a SMILES: that is the whole point of the demo question."""
    assert kb.lookup("CAND1", "P00001")["found"] is False
    r = kb.bio_kg_analogs("CAND1", "P00001")
    assert r["ranked_by_similarity"] is True and r["rows"]


def test_a_query_compound_without_smiles_falls_back_and_says_so(kb):
    r = kb.bio_kg_analogs("CAND2", "P00001", k=2)
    assert r["ranked_by_similarity"] is False
    assert r["similarity"] is None
    assert [row[1] for row in r["rows"]] == ["n/a", "n/a"]
    assert r["ic50_nM"] == [5.0, 50.0]            # the most potent instead, as a fallback
    assert "no usable structure" in r["summary"] and "spread" in r["summary"]
    assert r["target_potency_spread_nM"]["n"] == 4


def test_fingerprints_are_cached_per_load(kb):
    kb.bio_kg_analogs("CAND1", "P00001")
    cached = dict(kb._fps)
    assert {"CAND1", "CMP_A", "CMP_B", "CMP_OUT"} <= set(cached)
    kb.bio_kg_analogs("CAND1", "P00001")
    assert all(kb._fps[k] is v for k, v in cached.items())    # the same objects, not recomputed


def test_missing_entities_are_reported(kb):
    r = kb.bio_kg_analogs("NOPE", "P00001")
    assert r["rows"] == [] and "Could not resolve: NOPE" in r["summary"]
    assert r["compound_source"] == "unresolved"


@pytest.mark.parametrize("target", ["P00001", "CHEMBL0001", "Test kinase one"])
def test_a_target_resolves_by_id_chembl_id_or_name(kb, target):
    assert kb.bio_kg_analogs("CAND1", target)["ranked_by_similarity"] is True


def test_a_compound_outside_the_graph_is_still_ranked(kb, monkeypatch, tmp_path):
    """Addition 2: the similarity works from a resolved SMILES, not from a graph node, so a compound the KG
    never heard of still gets analogs on the target."""
    from agent.compounds import Compound, CompoundResolver
    from agent.tests.conftest import ANALOG_A

    class Stub(CompoundResolver):
        def from_dump(self, text):
            return Compound("CHEMBL_EXT", "external-compound", ANALOG_A, "ChEMBL dump")

    monkeypatch.setattr(kb, "_resolver", Stub(graph=kb, cache=tmp_path, allow_network=False),
                        raising=False)
    r = kb.bio_kg_analogs("external-compound", "P00001", k=3)
    assert r["compound_source"] == "ChEMBL dump" and r["compound_id"] == "CHEMBL_EXT"
    assert r["ranked_by_similarity"] is True
    assert r["similarity"][0] > 0.9                 # it is ANALOG_A's own structure
    assert "not in the knowledge graph" in r["summary"]
    ids = [row[0].split("(")[-1].rstrip(")") for row in r["rows"]]
    assert ids[0] == "CMP_A"


def test_an_off_graph_compound_is_flagged_by_resolve(kb, monkeypatch, tmp_path):
    from agent.compounds import Compound, CompoundResolver
    from agent.tests.conftest import ANALOG_A

    class Stub(CompoundResolver):
        def from_dump(self, text):
            return Compound("CHEMBL_EXT", "external-compound", ANALOG_A, "ChEMBL dump")

    monkeypatch.setattr(kb, "_resolver", Stub(graph=kb, cache=tmp_path, allow_network=False),
                        raising=False)
    r = kb.bio_kg_resolve("external-compound", "P00001")
    assert r["compound_in_graph"] is False and r["compound_source"] == "ChEMBL dump"
    assert r["target_classes"] == ["class:family", "class:kinase"]      # the target side still works
    assert "no measurement for it" in r["summary"]
