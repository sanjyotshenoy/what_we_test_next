"""Similar compounds anywhere in the graph (`bio_kg_similar`), as opposed to `bio_kg_analogs`, which only ranks
compounds measured on one target. This is the way in when the target itself has too few measurements, or when
the useful precedent is a well-studied relative's assay rather than its potency."""


def test_ranked_across_targets_with_what_each_is_measured_on(kb):
    r = kb.bio_kg_similar("CAND1", k=3)
    ids = [s["compound"] for s in r["similar"]]
    assert set(ids[:2]) == {"CMP_A", "CMP_B"}          # the near analogs, whichever target they sit on
    assert r["similar"][0]["similarity"] > r["similar"][-1]["similarity"]
    # CMP_A is measured on both targets, so both come back, most potent first
    cmp_a = next(s for s in r["similar"] if s["compound"] == "CMP_A")
    assert [m["target"] for m in cmp_a["measured_on"]] == ["P00001", "P00002"]
    assert cmp_a["measured_on"][0]["n_measurements"] == 2   # two IC50s on P00001, reported as their median
    assert cmp_a["measured_on"][0]["ic50_nM"] == 200


def test_k_limits_the_rows(kb):
    assert len(kb.bio_kg_similar("CAND1", k=1)["rows"]) == 1
    assert len(kb.bio_kg_similar("CAND1", k=2)["rows"]) == 2


def test_a_compound_without_a_structure_cannot_be_ranked(kb):
    r = kb.bio_kg_similar("CAND2")
    assert r["similar"] == []
    assert "no usable structure" in r["summary"]


def test_unresolvable_compound_says_so(kb):
    r = kb.bio_kg_similar("not-a-compound")
    assert r["rows"] == []
    assert r["compound_source"] == "unresolved"
