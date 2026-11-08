"""The deterministic concentration anchor (agent/anchor.py): the arithmetic, every edge case, the rule it is
bound to, and the grader-side consistency check in both failure directions."""
import math

import pytest

from kg.protocols.build_db import check_rule, load_rules
from wwtn.schema import Experiment, ExperimentProposal

from agent.anchor import (DEFAULT_SHAPE, FALLBACK_MULTIPLIER, TOLERANCE_STEPS, Shape, anchor_from_analogs,
                          anchor_from_result, check_series_consistent_with_analogs, series_from)

RULE = {r["id"]: r for r in load_rules()}["rule:agm/anchor_series_on_analogs"]
KINASE = Shape(dilution_factor=3.0, n_points=10, top_concentration_uM=10.0, source="proto:kinase_biochem_lum")


def analog(id, ic50, similarity=0.6, **extra):
    return {"compound": id, "name": id.lower(), "ic50_nM": ic50, "similarity": similarity, **extra}


def experiment(**overrides) -> Experiment:
    fields = {"assay_type": "biochemical kinase inhibition", "readout": "luminescence (ADP-Glo)",
              "system": "recombinant BTK", "top_concentration_uM": 1.15, "dilution_factor": 3.0,
              "n_points": 10, "replicates": 3, "controls": ["DMSO vehicle", "no-enzyme wells"]}
    return Experiment(**{**fields, **overrides})


# --- the arithmetic ------------------------------------------------------------------------------------------

def test_the_top_is_the_median_analog_potency_times_the_centring_multiplier():
    a = anchor_from_analogs([analog("C1", 4.0), analog("C2", 8.2), analog("C3", 19.0)], KINASE)
    assert a.applicable and a.confidence == "high" and a.flags == []
    assert a.median_ic50_nM == 8.2
    assert a.multiplier == pytest.approx(3.0 ** 4.5, rel=1e-3)        # 140.3x, derived from the shape
    assert a.top_concentration_uM == pytest.approx(8.2 * 3.0 ** 4.5 / 1000, rel=1e-2)
    assert a.statistic == "median (unweighted)" and a.weighting == "none" and a.weighting_reason


def test_the_series_is_centred_on_the_median_potency():
    """Half the points above the analogs' median, half below: the AGM sentence the rule quotes."""
    a = anchor_from_analogs([analog("C1", 8.2)], KINASE)
    median_uM = a.median_ic50_nM / 1000
    above = [c for c in a.series_uM if c > median_uM]
    below = [c for c in a.series_uM if c < median_uM]
    assert len(a.series_uM) == 10 and abs(len(above) - len(below)) <= 1
    assert a.low_concentration_uM == a.series_uM[-1] < median_uM < a.top_concentration_uM


def test_the_series_and_the_bounds_follow_the_template_shape():
    a = anchor_from_analogs([analog("C1", 10.0)], Shape(dilution_factor=2.97, n_points=9))
    assert len(a.series_uM) == 9 and a.dilution_factor == 2.97 and a.n_points == 9
    assert a.series_uM == series_from(a.top_concentration_uM, 2.97, 9)
    assert a.low_concentration_uM == pytest.approx(a.top_concentration_uM / 2.97 ** 8, rel=1e-2)


def test_the_derivation_is_recorded_in_full():
    a = anchor_from_analogs([analog("C1", 4.0, 0.61), analog("C2", 16.0, 0.55)], KINASE)
    d = a.to_dict()
    assert [x["compound"] for x in d["analogs"]] == ["C1", "C2"]
    assert [x["similarity"] for x in d["analogs"]] == [0.61, 0.55]
    assert d["median_ic50_nM"] == 10.0 and d["multiplier"] and d["multiplier_basis"]
    assert d["top_concentration_uM"] and d["low_concentration_uM"] and d["series_uM"]
    assert d["agm"]["nbk"] == "NBK92007" and "half the data points" in d["agm"]["quote"]
    assert "NBK92007" in d["multiplier_basis"]             # the multiplier says where it comes from
    assert d["template_default_uM"] == 10.0 and d["shift_log10"] > 0      # the anchor is below the default
    assert "median of 2 analog IC50(s)" in d["reason"]


def test_the_anchor_shifts_a_potent_compounds_series_down_from_the_template_default():
    a = anchor_from_analogs([analog("C1", 0.72), analog("C2", 8.2), analog("C3", 19.0)], KINASE)
    assert a.top_concentration_uM < KINASE.top_concentration_uM
    assert a.shift_log10 == pytest.approx(math.log10(10.0 / a.top_concentration_uM), abs=1e-3)


# --- the edge cases ------------------------------------------------------------------------------------------

def test_no_analogs_cannot_fire_and_says_to_fall_back_to_the_template_default():
    a = anchor_from_analogs([], KINASE)
    assert a.applicable is False and a.confidence == "none"
    assert a.top_concentration_uM is None and a.series_uM == []
    assert "no analog with a usable IC50" in a.reason
    assert "not applicable" in a.sentence() and "template's default" in a.sentence()
    assert a.rule_context() == {}                  # nothing to check the rule with: a judge item


def test_one_analog_fires_but_is_flagged_low_confidence():
    a = anchor_from_analogs([analog("C1", 8.2)], KINASE)
    assert a.applicable is True and a.confidence == "low" and a.flags == ["single_analog"]
    assert a.median_ic50_nM == 8.2 and a.n_analogs == 1
    assert "single_analog" in a.reason


def test_a_spread_over_three_orders_of_magnitude_fires_but_is_flagged():
    a = anchor_from_analogs([analog("C1", 0.5), analog("C2", 50.0), analog("C3", 5000.0)], KINASE)
    assert a.applicable is True and a.confidence == "low" and "wide_spread" in a.flags
    assert a.spread_log10 == pytest.approx(4.0, abs=0.01)
    assert a.median_ic50_nM == 50.0        # the median is still the median
    narrow = anchor_from_analogs([analog("C1", 5.0), analog("C2", 50.0), analog("C3", 100.0)], KINASE)
    assert "wide_spread" not in narrow.flags and narrow.confidence == "high"


@pytest.mark.parametrize("bad, why", [
    ({"ic50_nM": None}, "no IC50 value"),
    ({"ic50_nM": ">128"}, "censored"),
    ({"ic50_nM": "<0.1"}, "censored"),
    ({"ic50_nM": 100.0, "relation": ">"}, "censored"),
    ({"ic50_nM": 0.0}, "non-positive"),
    ({"ic50_nM": float("nan")}, "non-positive or non-finite"),
    ({"ic50_nM": "about 5"}, "unparseable"),
])
def test_censored_or_missing_values_are_skipped_and_counted(bad, why):
    rows = [analog("GOOD1", 8.0), analog("GOOD2", 8.4), {**analog("BAD", 1.0), **bad}]
    a = anchor_from_analogs(rows, KINASE)
    assert a.n_analogs == 2 and a.n_skipped == 1
    assert [x["compound"] for x in a.analogs] == ["GOOD1", "GOOD2"]
    assert a.skipped[0]["compound"] == "BAD" and why in a.skipped[0]["why"]
    assert "skipped_1" in a.flags and a.median_ic50_nM == pytest.approx(8.2)


def test_every_analog_censored_is_the_no_analogs_case_with_the_count():
    a = anchor_from_analogs([{**analog("BAD", 1.0), "ic50_nM": ">128"}], KINASE)
    assert a.applicable is False and a.n_skipped == 1 and a.n_analogs == 0
    assert "1 analog(s) skipped" in a.reason


def test_a_numeric_string_potency_is_still_usable():
    a = anchor_from_analogs([analog("C1", "8.2")], KINASE)
    assert a.applicable and a.median_ic50_nM == 8.2


def test_without_a_template_shape_the_multiplier_is_the_flagged_heuristic():
    a = anchor_from_analogs([analog("C1", 8.0), analog("C2", 8.4)], Shape(dilution_factor=0, n_points=0))
    assert a.multiplier == FALLBACK_MULTIPLIER and "TODO(final)" in a.multiplier_basis
    assert "heuristic_multiplier" in a.flags and a.confidence == "low"
    assert "not an AGM number" in a.multiplier_basis


def test_the_default_shape_is_the_agm_one_when_no_template_is_passed():
    a = anchor_from_analogs([analog("C1", 8.0), analog("C2", 8.4)])
    assert (a.dilution_factor, a.n_points) == (DEFAULT_SHAPE.dilution_factor, DEFAULT_SHAPE.n_points)
    assert a.confidence == "high" and "heuristic_multiplier" not in a.flags


def test_unranked_analogs_fire_but_are_flagged_as_not_structural():
    """A query compound with no usable structure: bio_kg_analogs returns the target's most potent compounds
    instead, which is a weaker prior than structural analogs, so the anchor says so."""
    a = anchor_from_analogs([analog("C1", 5.0, None), analog("C2", 50.0, None)], KINASE, ranked=False)
    assert a.applicable and a.confidence == "low" and "not_ranked_by_similarity" in a.flags


# --- from a real tool result ---------------------------------------------------------------------------------

def test_the_anchor_reads_a_bio_kg_analogs_result(kb):
    result = kb.bio_kg_analogs("CAND1", "P00001", k=3)
    a = anchor_from_result(result)
    assert [x["compound"] for x in a.analogs] == [r["compound"] for r in result["analogs"]]
    assert a.median_ic50_nM == pytest.approx(50.0)           # CMP_A 200, CMP_B 50, CMP_OUT 5 nM
    assert a.applicable and a.n_analogs == 3


def test_a_shape_is_read_off_a_template_detail_or_is_none(kb):
    from agent.propose import shape_of

    detail = {"id": "proto:x", "params": {"top_concentration": {"value": 12, "unit": "uM"},
                                          "dilution_factor": {"value": 2.97}, "n_points": {"value": 9}}}
    shape = Shape.from_template(detail)
    assert (shape.dilution_factor, shape.n_points, shape.top_concentration_uM) == (2.97, 9, 12.0)
    assert shape.source == "proto:x"
    # the fixture template carries only a top concentration, so it yields no shape at all, not a guess
    assert Shape.from_template({"params": {"top_concentration": {"value": 10}}}) is None
    assert shape_of(kb.protocol_kg_templates("potency", target="P00001")) is None


def test_a_structure_less_query_compound_is_flagged_through_the_result(kb):
    result = kb.bio_kg_analogs("CAND2", "P00001", k=2)
    a = anchor_from_result(result)
    assert result["ranked_by_similarity"] is False
    assert a.applicable and "not_ranked_by_similarity" in a.flags and a.confidence == "low"


# --- the rule binding ----------------------------------------------------------------------------------------

def test_the_rule_and_the_anchor_function_do_not_drift():
    """One binding, two implementations: rules.yaml's expression and agent/anchor.py must agree."""
    a = anchor_from_analogs([analog("C1", 8.2)], KINASE)
    design = {**experiment(top_concentration_uM=a.top_concentration_uM).model_dump(), **a.rule_context()}
    assert check_rule(RULE, design) is True
    ignored = {**experiment(top_concentration_uM=10.0).model_dump(), **a.rule_context()}
    assert check_rule(RULE, ignored) is False            # the generic template default, analogs ignored


def test_the_rule_is_a_judge_item_when_the_anchor_cannot_fire():
    a = anchor_from_analogs([], KINASE)
    design = {**experiment().model_dump(), **a.rule_context()}
    assert check_rule(RULE, design) is None


# --- the grader-side check -----------------------------------------------------------------------------------

ANALOGS = [analog("CHEMBL2057912", 8.2, 0.597), analog("CHEMBL1873475", 0.72, 0.578),
           analog("CHEMBL3647964", 19.0, 0.578)]
ANCHORED = anchor_from_analogs(ANALOGS, KINASE).top_concentration_uM


def test_a_series_on_the_anchor_passes():
    check = check_series_consistent_with_analogs(experiment(top_concentration_uM=ANCHORED), ANALOGS,
                                                 citations=["CHEMBL2057912", "CHEMBL1873475"])
    assert check.passed and bool(check) is True
    assert "dilution steps from the analog anchor" in check.reason
    assert check.anchor is not None and check.anchor.applicable
    assert check.to_dict()["anchor"]["median_ic50_nM"] == 8.2


def test_failure_direction_one_a_series_that_ignores_the_retrieved_analogs():
    """The template's generic 10 µM top against analogs at 0.72-19 nM: >1 dilution step off the anchor."""
    check = check_series_consistent_with_analogs(experiment(top_concentration_uM=10.0), ANALOGS,
                                                 citations=["CHEMBL2057912"])
    assert check.passed is False
    assert "not centred on the analogs" in check.reason and "dilution steps" in check.reason


def test_failure_direction_one_also_catches_a_series_that_does_not_span_the_median():
    check = check_series_consistent_with_analogs(
        experiment(top_concentration_uM=0.001, n_points=3), ANALOGS, citations=[])
    assert check.passed is False and "does not even span the analogs' median" in check.reason


def test_failure_direction_two_citing_analogs_it_did_not_retrieve():
    check = check_series_consistent_with_analogs(
        experiment(top_concentration_uM=ANCHORED), ANALOGS,
        citations=["CHEMBL2057912", "CHEMBL9999999"])      # the second was never returned
    assert check.passed is False
    assert "never returned" in check.reason and "CHEMBL9999999" in check.reason


def test_failure_direction_two_from_the_models_own_stated_analogs():
    check = check_series_consistent_with_analogs(experiment(top_concentration_uM=ANCHORED), ANALOGS,
                                                 cited_analogs=["CMP_MADE_UP"])
    assert check.passed is False and "CMP_MADE_UP" in check.reason


def test_the_query_compound_is_not_mistaken_for_a_cited_analog():
    check = check_series_consistent_with_analogs(
        experiment(top_concentration_uM=ANCHORED), ANALOGS,
        citations=["CHEMBL5593141", "Q06187", "proto:kinase_biochem_lum"], query_compound="CHEMBL5593141")
    assert check.passed, check.reason


def test_the_check_reads_an_experiment_proposal_and_its_citations():
    proposal = ExperimentProposal(question_id="q1", answerable_from_kb=False,
                                  experiment=experiment(top_concentration_uM=ANCHORED),
                                  citations=["CHEMBL1873475", "Q06187"])
    assert check_series_consistent_with_analogs(proposal, ANALOGS).passed
    bad = ExperimentProposal(question_id="q1", answerable_from_kb=False,
                             experiment=experiment(top_concentration_uM=10.0),
                             citations=["CHEMBL1873475"])
    assert check_series_consistent_with_analogs(bad, ANALOGS).passed is False


def test_the_check_takes_a_whole_tool_result(kb):
    result = kb.bio_kg_analogs("CAND1", "P00001", k=3)
    anchor = anchor_from_result(result, KINASE)
    good = check_series_consistent_with_analogs(experiment(top_concentration_uM=anchor.top_concentration_uM),
                                                result, cited_analogs=["CMP_A"])
    assert good.passed, good.reason
    assert check_series_consistent_with_analogs(experiment(top_concentration_uM=500.0), result).passed is False


def test_with_no_analogs_there_is_nothing_to_contradict():
    check = check_series_consistent_with_analogs(experiment(top_concentration_uM=10.0), [])
    assert check.passed and "no analog anchor" in check.reason
    # but a fabricated analog citation still fails, even with nothing retrieved
    assert check_series_consistent_with_analogs(experiment(), [], citations=["CHEMBL9999999"]).passed is False


def test_the_check_rejects_a_design_without_a_usable_series():
    assert check_series_consistent_with_analogs({"n_points": 10}, ANALOGS).passed is False
    assert check_series_consistent_with_analogs(
        {"top_concentration_uM": 1.0, "dilution_factor": 1.0, "n_points": 10}, ANALOGS).passed is False


def test_the_tolerance_is_one_dilution_step_by_default():
    just_inside = ANCHORED * 3.0 ** (TOLERANCE_STEPS * 0.95)
    just_outside = ANCHORED * 3.0 ** (TOLERANCE_STEPS * 1.2)
    assert check_series_consistent_with_analogs(experiment(top_concentration_uM=just_inside), ANALOGS).passed
    assert check_series_consistent_with_analogs(experiment(top_concentration_uM=just_outside),
                                                ANALOGS).passed is False
