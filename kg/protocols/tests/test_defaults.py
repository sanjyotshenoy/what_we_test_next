"""How a parameter's default is chosen (kg/protocols/defaults.py): the reference run for the series
parameters, nearest-to-centre for the rest, canonical snapping, the dispersion flag, and the derivation text
that has to be on every default. Plus a regression test pinning what the curated kinase template resolves to.

The `graph` fixture is in conftest.py."""
import math

import pytest

from kg.protocols.build_db import load_templates
from kg.protocols.defaults import (CANONICAL_SPACINGS, DefaultError, centre_of, resolve_parameters, snap)

RULES = {"reference run", "nearest to centre", "modal value", "only observation"}


def template(parameters: dict, exemplars: list[dict] | None = None) -> dict:
    """A minimal template: only `exemplars` (for the listing order) and `parameters` matter here."""
    aids = sorted({o["aid"] for p in parameters.values() for o in p["observed"] if o.get("aid")})
    return {"id": "proto:test", "exemplars": exemplars or [{"aid": aid} for aid in aids],
            "parameters": parameters}


def observation(value, unit, aid, quote="quoted span"):
    return {"value": value, "unit": unit, "aid": aid, "quote": quote}


def params(nodes):
    return {n["name"]: n["props"] for n in nodes.values() if n["type"] == "Parameter"
            and n["id"].startswith("proto:kinase_biochem_lum/")}


# --- the centre -------------------------------------------------------------------------------------------

def test_centre_is_the_geometric_median_on_a_log_scale_and_the_median_on_a_linear_one():
    assert centre_of([10.0, 1000.0], "log") == pytest.approx(100.0)        # not the arithmetic mean, 505
    assert centre_of([10.0, 100.0, 1000.0], "log") == pytest.approx(100.0)
    assert centre_of([10.0, 1000.0], "linear") == pytest.approx(505.0)
    with pytest.raises(DefaultError):
        centre_of([0.0, 10.0], "log")


# --- 1. the reference run ---------------------------------------------------------------------------------

def test_series_parameters_come_from_one_exemplar_in_every_curated_template():
    for id, curated in load_templates().items():
        resolved = resolve_parameters(curated)
        series = {name: props for name, props in resolved.items() if props["series_parameter"]}
        assert series, id
        exemplars = {props["from_exemplar"] for props in series.values()}
        assert len(exemplars) == 1, f"{id}: series parameters came from {exemplars}"
        reference = exemplars.pop()
        for name, props in series.items():
            assert props["default_rule"] == "reference run"
            assert props["reference_exemplar"] == reference
            assert "no_reference_run" not in props["flags"]
            # the reference run really reports this parameter: the value is one of its own observations
            quoted = [o for o in props["observed"] if f"aid:{o.get('aid')}" == reference
                      or f"file:{o.get('file')}" == reference]
            assert len(quoted) == 1 and quoted[0]["quote"] == props["quote"]


def test_the_reference_run_is_the_candidate_nearest_the_centre_not_the_first_listed():
    """40 uM / 3-fold / 10 points is the consistent series; the first-listed exemplar is the odd one out."""
    resolved = resolve_parameters(template({
        "top_concentration": {"observed": [observation(1000, "uM", 1), observation(40, "uM", 2),
                                           observation(40, "uM", 3), observation(50, "uM", 4)]},
        "dilution_factor": {"observed": [observation(10, "fold", 1), observation(3, "fold", 2),
                                         observation(3, "fold", 3), observation(3, "fold", 4)]},
        "n_points": {"observed": [observation(5, "concentrations", 1), observation(10, "concentrations", 2),
                                  observation(10, "concentrations", 3), observation(10, "concentrations", 4)]},
    }))
    assert {name: props["value"] for name, props in resolved.items()} == {
        "top_concentration": 40, "dilution_factor": 3, "n_points": 10}
    assert {props["from_exemplar"] for props in resolved.values()} == {"aid:2"}
    assert resolved["top_concentration"]["reference_run_candidates"]["aid:1"] > \
        resolved["top_concentration"]["reference_run_candidates"]["aid:2"]


def test_a_series_parameter_no_exemplar_reports_in_full_is_flagged_not_quietly_mixed():
    """AID 1 has the top concentration, AID 2 the spacing: there is no reference run, and the defaults say so
    instead of pretending the mixture is a series somebody ran."""
    resolved = resolve_parameters(template({
        "top_concentration": {"observed": [observation(10, "uM", 1)]},
        "dilution_factor": {"observed": [observation(3, "fold", 2)]},
    }))
    for name, props in resolved.items():
        assert "no_reference_run" in props["flags"], name
        assert props["exemplars_disagree"] and "NOT guaranteed" in props["derivation"]


# --- 2. nearest to centre ---------------------------------------------------------------------------------

def test_a_default_is_always_a_value_some_exemplar_really_used():
    """Never a computed average: 25 / 5 / 5 / 5 uL resolves to 5, not to the mean 10."""
    resolved = resolve_parameters(template({"detection_reagent_volume": {"observed": [
        observation(25, "uL", 1), observation(5, "uL", 2), observation(5, "uL", 3), observation(5, "uL", 4)]}}))
    props = resolved["detection_reagent_volume"]
    assert props["value"] == 5 and props["from_exemplar"] == "aid:2"
    assert props["default_rule"] == "nearest to centre" and props["centre"] == 5


def test_mixed_units_are_compared_in_one_unit_before_the_centre_is_taken():
    """2 h, 120 min, 60, 60, 60 -> 60 min (the median once the hours are converted), not 2 h for being first."""
    resolved = resolve_parameters(template({"reaction_time": {"observed": [
        observation(2, "h", 1), observation(120, "min", 2), observation(60, "min", 3),
        observation(60, "min", 4), observation(60, "min", 5)]}}))
    props = resolved["reaction_time"]
    assert (props["value"], props["unit"], props["from_exemplar"]) == (60, "min", "aid:3")
    assert props["centre"] == 60 and props["centre_unit"] == "min"


def test_a_word_among_the_numbers_is_resolved_by_the_modal_value_not_by_averaging():
    resolved = resolve_parameters(template({"temperature": {"observed": [
        observation(28, "C", 1), observation("room temperature", None, 2),
        observation("room temperature", None, 3)]}}))
    props = resolved["temperature"]
    assert props["value"] == "room temperature" and props["default_rule"] == "modal value"
    assert props["from_exemplar"] == "aid:2" and props["centre"] is None
    assert "mixed_value_kinds" in props["flags"] and props["exemplars_disagree"]


def test_observations_from_different_dimensions_fail_loudly():
    with pytest.raises(DefaultError, match="mix dimensions"):
        resolve_parameters(template({"volume": {"observed": [observation(5, "uL", 1),
                                                             observation(5, "uM", 2)]}}))


# --- 3. canonical snapping --------------------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [(2.97, 3.0), (3.0, 3.0), (2.05, 2.0), (9.6, 10.0),
                                             (3.2, math.sqrt(10)), (2.44, 2.5)])
def test_snapping_fires_inside_the_tolerance(value, expected):
    snapped, target = snap(value)
    assert snapped == pytest.approx(expected) and target == pytest.approx(expected)


@pytest.mark.parametrize("value", [3.6, 1.5, 6.5, 7.0, 2.2])
def test_snapping_does_not_fire_outside_the_tolerance(value):
    snapped, target = snap(value)
    assert snapped == value and target is None
    assert min(abs(value - step) / step for step in CANONICAL_SPACINGS) > 0.05


def test_a_snapped_default_records_what_it_was_snapped_from():
    resolved = resolve_parameters(template({
        "top_concentration": {"observed": [observation(12, "uM", 1), observation(10, "uM", 2)]},
        "dilution_factor": {"observed": [observation(2.97, "fold", 1), observation(3.0, "fold", 2)]},
        "n_points": {"observed": [observation(9, "concentrations", 1), observation(9, "concentrations", 2)]},
    }))
    props = resolved["dilution_factor"]
    assert props["value"] == 3.0 and props["snapped"] is True
    assert props["snapped_from"] == 2.97 and props["snapped_to"] == 3.0
    assert props["aid"] == 1 and props["quote"]       # still attributed to the exemplar it was read from
    assert "Snapped 2.97 fold to the canonical 3-fold step" in props["derivation"]
    assert "off_ladder" not in props["flags"]


def test_an_unsnappable_spacing_is_kept_and_flagged_rather_than_forced():
    resolved = resolve_parameters(template({"dilution_factor": {"observed": [observation(3.6, "fold", 1)]}}))
    props = resolved["dilution_factor"]
    assert props["value"] == 3.6 and props["snapped"] is False and props["snapped_to"] is None
    assert "off_ladder" in props["flags"] and "flagged rather than forced" in props["derivation"]


# --- 4. the derivation on every default -------------------------------------------------------------------

def test_every_default_in_the_graph_records_its_derivation(graph):
    nodes, _ = graph
    parameters = [n for n in nodes.values() if n["type"] == "Parameter"]
    assert len(parameters) >= 39
    for node in parameters:
        props = node["props"]
        assert props["value"] is not None, node["id"]
        assert props["default_rule"] in RULES, node["id"]
        assert len(props["derivation"]) > 40 and props["derivation"].startswith(props["default_rule"])
        assert props["from_exemplar"] and (props["aid"] or props.get("file")), node["id"]
        assert props["quote"] and props["observed"] and props["n_exemplars"] >= 1
        assert isinstance(props["exemplars_disagree"], bool) and isinstance(props["flags"], list)
        if props["default_rule"] == "modal value":
            assert props["centre"] is None and props["scale"] == "categorical"
        else:
            assert props["centre"] is not None and props["centre_rule"] in ("median", "geometric median")
            assert props["spread"]["min"] <= props["normalized_value"] or props["snapped"]
        if props["series_parameter"]:
            assert props["reference_exemplar"] or "no_reference_run" in props["flags"]


def test_no_default_is_just_the_first_observation_by_construction():
    """The old `_first` is gone; nothing in build_db falls back to observed[0]."""
    import kg.protocols.build_db as build_db
    assert not hasattr(build_db, "_first")
    with pytest.raises(DefaultError, match="no observations"):
        resolve_parameters(template({"empty": {"observed": []}}))
    with pytest.raises(DefaultError, match="neither an AID nor a file"):
        resolve_parameters({"id": "proto:test", "exemplars": [],
                            "parameters": {"p": {"observed": [{"value": 1, "unit": "uM", "quote": "q"}]}}})


# --- 5. the dispersion flag -------------------------------------------------------------------------------

def test_the_dispersion_flag_fires_on_a_decade_of_spread_on_a_log_scale_parameter():
    resolved = resolve_parameters(template({"atp_concentration": {"observed": [
        observation(10, "uM", 1), observation(0.1, "mM", 2)]}}))
    props = resolved["atp_concentration"]
    assert props["flags"] == ["wide_spread"] and props["exemplars_disagree"]
    assert "a single default is misleading" in props["derivation"]
    assert props["spread"]["decades"] == pytest.approx(1.0)


def test_the_dispersion_flag_does_not_fire_when_the_exemplars_agree():
    resolved = resolve_parameters(template({"mgcl2_concentration": {"observed": [
        observation(10, "mM", 1), observation(10, "mM", 2), observation(11, "mM", 3)]}}))
    props = resolved["mgcl2_concentration"]
    assert props["flags"] == [] and props["exemplars_disagree"] is False
    assert "misleading" not in props["derivation"]


def test_the_dispersion_flag_fires_on_a_linear_spread_wider_than_the_centre():
    resolved = resolve_parameters(template({"cells_per_well": {"observed": [
        observation(5000, "cells/well", 1), observation(5000, "cells/well", 2),
        observation(500, "cells/well", 3), observation(1250, "cells/well", 4)]}}))
    props = resolved["cells_per_well"]
    assert props["value"] == 5000 and "wide_spread" in props["flags"] and props["exemplars_disagree"]


# --- 6. regression: what the curated kinase template actually resolves to ---------------------------------

def test_kinase_template_defaults_are_what_this_branch_derived(graph):
    """Pinned outcomes for proto:kinase_biochem_lum (before -> after this change):

    - the series comes from AID 588811 as a reference run (it and 602295 are the only exemplars reporting top
      concentration, spacing and points; 588811's series is nearer the centre: 2.00 vs 2.27 normalized). Top
      concentration 12 uM (unchanged, but now derived: the 46 uM of 623998/623999 are the top of two
      interleaved series, and neither AID reports a spacing or a point count, so neither can be a reference
      run), spacing 2.97 -> 3.0 fold (snapped), 9 points (unchanged).
    - kinase_reaction_time 2 h -> 60 min (AID 623998; the median once 2 h and 120 min are converted).
    - kinase_reaction_temperature 28 C -> "room temperature" (AID 602295, 2 of 3 exemplars).
    - detection_reagent_time 40 -> 30 min (AID 623998, 3 of 4 exemplars).
    - atp_stock_concentration 20 -> 50 uM (AID 602295, nearest the 83.7 uM geometric median), flagged: the
      exemplars span 20-903 uM because ATP is chosen per kinase.
    - flagged as genuinely disagreeing: atp_final_concentration (10 vs 100 uM), atp_stock_concentration,
      kinase_reaction_temperature. Nothing else in this template.
    """
    nodes, _ = graph
    kinase = params(nodes)

    series = {name: kinase[name] for name in ("top_concentration", "dilution_factor", "n_points")}
    assert {props["reference_exemplar"] for props in series.values()} == {"aid:588811"}
    assert [props["value"] for props in series.values()] == [12, 3.0, 9]
    assert series["top_concentration"]["unit"] == "uM" and series["top_concentration"]["aid"] == 588811
    assert series["top_concentration"]["centre"] == pytest.approx(23.4947, abs=1e-3)
    assert series["dilution_factor"]["snapped_from"] == 2.97
    assert series["dilution_factor"]["reference_run_candidates"] == {"aid:588811": 2.0, "aid:602295": 2.2714}

    assert (kinase["kinase_reaction_time"]["value"], kinase["kinase_reaction_time"]["unit"]) == (60, "min")
    assert kinase["kinase_reaction_time"]["aid"] == 623998
    assert kinase["kinase_reaction_temperature"]["value"] == "room temperature"
    assert kinase["kinase_reaction_temperature"]["aid"] == 602295
    assert (kinase["detection_reagent_time"]["value"], kinase["detection_reagent_time"]["aid"]) == (30, 623998)
    assert (kinase["atp_stock_concentration"]["value"], kinase["atp_stock_concentration"]["aid"]) == (50, 602295)

    flagged = {name for name, props in kinase.items() if props["exemplars_disagree"]}
    assert flagged == {"atp_final_concentration", "atp_stock_concentration", "kinase_reaction_temperature"}


def test_the_other_two_curated_templates_keep_their_series_and_name_their_flags(graph):
    """proto:cell_viability_atp: series from AID 1691 (40 uM, 3-fold, 10 points; a tie with 1699/1972 broken by
    the template's exemplar order). proto:bacterial_mic_broth: series from AID 449774, the only exemplar
    reporting all three (50 uM, 2-fold - already canonical, so no snap - 10 points)."""
    nodes, _ = graph
    viability = {n["name"]: n["props"] for n in nodes.values() if n["type"] == "Parameter"
                 and n["id"].startswith("proto:cell_viability_atp/")}
    mic = {n["name"]: n["props"] for n in nodes.values() if n["type"] == "Parameter"
           and n["id"].startswith("proto:bacterial_mic_broth/")}

    assert [viability[n]["value"] for n in ("top_concentration", "dilution_factor", "n_points")] == [40, 3, 10]
    assert {viability[n]["reference_exemplar"] for n in ("top_concentration", "n_points")} == {"aid:1691"}
    assert "ties with" in viability["top_concentration"]["derivation"]

    assert [mic[n]["value"] for n in ("top_concentration", "dilution_factor", "n_points")] == [50, 2, 10]
    assert {mic[n]["reference_exemplar"] for n in ("top_concentration", "n_points")} == {"aid:449774"}
    assert mic["dilution_factor"]["snapped"] is False        # 2-fold is already on the ladder
    assert mic["plate_wells"]["value"] == 96 and "wide_spread" in mic["plate_wells"]["flags"]


def test_a_modal_default_with_no_majority_says_it_is_a_coin_flip():
    resolved = resolve_parameters(template({"incubation_time": {"observed": [
        observation("overnight", None, 1, "grown overnight"), observation(18, "h", 2)]}}))
    props = resolved["incubation_time"]
    assert props["default_rule"] == "modal value" and props["value"] == "overnight"
    assert "no_majority" in props["flags"] and props["exemplars_disagree"]
    assert "coin-flip" in props["derivation"]
