"""Class-chain template lookup and question-type routing (problems 1 and 2 of DISCUSSIONS.md "Merging
kg-scaffolding"): a target sits in a narrow class while the templates hang off a broad one."""


def test_resolve_returns_the_whole_class_chain(kb):
    r = kb.bio_kg_resolve("CAND1", "P00001")
    assert r["compound_id"] == "CAND1" and r["target_id"] == "P00001"
    # most specific first, up MEMBER_OF then SUBCLASS_OF
    assert r["target_classes"] == ["class:family", "class:kinase"]
    assert r["template_classes"] == ["class:kinase"]       # the broad class is where templates hang
    assert ["class:kinase", "TargetClass", "Protein Kinase"] in r["rows"]
    assert "Protein Kinase (class:kinase)" in r["summary"]


def test_templates_found_through_the_chain(kb):
    r = kb.protocol_kg_templates("potency", target="P00001")
    assert [t["id"] for t in r["templates"]] == ["proto:biochem"]
    assert r["via_classes"] == ["class:kinase"]            # not the target's own class
    assert r["templates"][0]["steps"] == ["Dilute the compound.", "Read luminescence."]
    assert r["templates"][0]["params"]["top_concentration"] == {"value": 10, "unit": "uM"}


def test_a_target_on_the_broad_class_still_works(kb):
    r = kb.protocol_kg_templates("potency", target="P00002")
    assert [t["id"] for t in r["templates"]] == ["proto:biochem"]


def test_target_class_argument_still_accepted(kb):
    """Backwards compatibility: the old signature took a class ID."""
    narrow = kb.protocol_kg_templates("potency", "class:family")
    assert [t["id"] for t in narrow["templates"]] == ["proto:biochem"]   # walks up from the class too
    broad = kb.protocol_kg_templates("potency", "class:kinase")
    assert [t["id"] for t in broad["templates"]] == ["proto:biochem"]


def test_question_type_routes_by_answers_edges(kb):
    assert [t["id"] for t in kb.protocol_kg_templates("potency", target="P00001")["templates"]] == ["proto:biochem"]
    cells = kb.protocol_kg_templates("cellular_potency", target="P00001")
    assert [t["id"] for t in cells["templates"]] == ["proto:cells"]


def test_question_type_aliases_are_normalised(kb):
    for alias in ("cellular_activity", "Cellular Activity", "qtype:cellular_potency", "cell_viability"):
        r = kb.protocol_kg_templates(alias, target="P00001")
        assert [t["id"] for t in r["templates"]] == ["proto:cells"], alias
        assert r["question_type"] == "cellular_potency"


def test_no_match_returns_none_and_says_which_types_exist(kb):
    r = kb.protocol_kg_templates("binding", target="P00001")
    assert r["templates"] == [] and r["rows"] == []
    assert r["question_types_available"] == ["cellular_potency", "potency"]
    assert "No template for a binding question" in r["summary"]
    assert "cellular_potency, potency" in r["summary"]


def test_a_non_kinase_target_gets_its_own_template(kb):
    r = kb.protocol_kg_templates("potency", target="P00003")
    assert [t["id"] for t in r["templates"]] == ["proto:protease"]


def test_a_target_outside_the_graph_has_no_templates(kb):
    r = kb.protocol_kg_templates("potency", target="P99999")
    assert r["templates"] == [] and "No template in the protocol KG applies" in r["summary"]
