"""The AGM rules: well-formed entries, and the machine-checkable ones evaluated over wwtn.schema.Experiment."""
import pytest

from kg.protocols.build_db import check_rule, load_archetypes, load_rules
from wwtn.schema import Experiment

RULES = {r["id"]: r for r in load_rules()}


def experiment(**overrides) -> dict:
    """A sound kinase IC50 design (10 points, 3-fold, top 10 uM, DMSO + staurosporine), as a dict for check_rule."""
    base = Experiment(
        assay_type="biochemical kinase activity, luminescent ADP detection",
        readout="luminescence (ADP-Glo)", system="recombinant DYRK1A",
        top_concentration_uM=10.0, dilution_factor=3.0, n_points=10, replicates=3,
        controls=["DMSO vehicle", "no-enzyme wells"],
    )
    return {**base.model_dump(), "expected_ic50_uM": 0.05, **overrides}


def test_rules_are_well_formed():
    rules = load_rules()
    assert 10 <= len(rules) <= 20
    archetypes = set(load_archetypes())
    for rule in rules:
        assert rule["id"].startswith("rule:agm/")
        assert rule["text"].strip() and rule["severity"] in ("must", "should")
        assert rule["applies_to"] == "all" or set(rule["applies_to"]) <= archetypes
        assert rule["source"]["nbk"].startswith("NBK") and rule["source"]["chapter"]
        assert len(rule["source"]["quote"]) > 20
    assert len({r["id"] for r in rules}) == len(rules)


def test_some_rules_are_machine_checkable_and_the_rest_are_judge_items():
    checkable = [r for r in load_rules() if r.get("check")]
    assert 5 <= len(checkable) <= 20
    assert all(check_rule(r, experiment()) is not None for r in checkable)
    assert all(check_rule(r, experiment()) is None for r in load_rules() if not r.get("check"))


def test_a_sound_design_passes_every_checkable_rule():
    for rule in load_rules():
        assert check_rule(rule, experiment()) is not False, rule["id"]


@pytest.mark.parametrize("rule_id, bad", [
    ("rule:agm/min_points_enzyme_ic50", {"n_points": 9}),
    ("rule:agm/min_points_crc", {"n_points": 5}),
    ("rule:agm/even_spacing", {"dilution_factor": 10.0}),
    ("rule:agm/vehicle_control", {"controls": ["staurosporine", "no-enzyme wells"]}),
    ("rule:agm/max_min_controls", {"controls": ["DMSO vehicle"]}),
    # a series topping out at 10 uM is far above a 0.1 nM inhibitor: the curve has no bottom
    ("rule:agm/bracket_expected_ic50", {"expected_ic50_uM": 0.0001}),
])
def test_each_check_catches_its_own_failure(rule_id, bad):
    assert check_rule(RULES[rule_id], experiment()) is True
    assert check_rule(RULES[rule_id], experiment(**bad)) is False


def test_check_returns_none_when_context_is_missing_or_nonsensical():
    missing = experiment()
    del missing["expected_ic50_uM"]
    assert check_rule(RULES["rule:agm/bracket_expected_ic50"], missing) is None
    assert check_rule(RULES["rule:agm/bracket_expected_ic50"], experiment(expected_ic50_uM=0.0)) is None


def test_mic_archetype_is_exempt_from_the_three_fold_spacing_rule():
    spacing = RULES["rule:agm/even_spacing"]
    assert "proto:bacterial_mic_broth" not in spacing["applies_to"]
    assert check_rule(RULES["rule:agm/min_points_crc"], experiment(dilution_factor=2.0, n_points=10)) is True
