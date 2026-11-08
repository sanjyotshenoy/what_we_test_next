"""The worked example on the real seed graph, skipped when kg/*/graph are absent.

The kinase template's curated default series is generic across compounds (top 12 µM, 2.97-fold, 9 points, read
from PubChem AIDs 588811/602295/623998), so it bottoms out at ~2 nM — above the most potent of this compound's
analogs. The demo compound's nearest BTK analogs sit at 0.72-19 nM, so the anchor has to move the whole series
down. That shift is the point of agent/anchor.py, and this test is what says the real numbers still do it.
"""
import pytest

from agent.anchor import anchor_from_result, check_series_consistent_with_analogs
from agent.kg_backend import KG_ROOT
from agent.propose import shape_of
from agent.tools import DEMO_COMPOUND, DEMO_TARGET, KnowledgeBase

pytestmark = pytest.mark.skipif(
    not all((KG_ROOT / g / "graph" / "nodes.csv").exists() for g in ("biology", "protocols")),
    reason="the real graphs (kg/*/graph) are not built here")


@pytest.fixture(scope="module")
def seed():
    kb = KnowledgeBase()
    assert not kb.sample, "the real graphs should be in use when this test runs"
    analogs = kb.bio_kg_analogs(DEMO_COMPOUND, DEMO_TARGET, k=3)
    templates = kb.protocol_kg_templates("potency", target=DEMO_TARGET)
    return kb, analogs, templates


def test_the_anchor_shifts_the_series_down_from_the_template_default(seed):
    _, analogs, templates = seed
    shape = shape_of(templates)
    assert shape and shape.source == "proto:kinase_biochem_lum"
    assert (shape.top_concentration_uM, shape.n_points) == (12.0, 9)      # the curated generic default

    anchor = anchor_from_result(analogs, shape)
    assert anchor.applicable and anchor.confidence == "high" and anchor.flags == []
    assert anchor.n_analogs == 3 and anchor.n_skipped == 0
    assert set(anchor.analog_ids) == {"CHEMBL2057912", "CHEMBL1873475", "CHEMBL3647964"}
    assert anchor.median_ic50_nM == pytest.approx(8.2)

    # the whole series moves down by more than a decade, and now brackets the analogs instead of sitting above
    assert anchor.top_concentration_uM < shape.top_concentration_uM / 10
    assert anchor.shift_log10 > 1.0
    default_lowest = shape.top_concentration_uM / shape.dilution_factor ** (shape.n_points - 1)
    most_potent = min(a["ic50_nM"] for a in anchor.analogs) / 1000
    assert most_potent < default_lowest, "the generic default's bottom point is above the best analog"
    assert anchor.low_concentration_uM < most_potent, "the anchored series reaches below it"
    assert anchor.low_concentration_uM < anchor.median_ic50_nM / 1000 < anchor.top_concentration_uM


def test_the_template_default_fails_the_consistency_check_and_the_anchor_passes(seed):
    _, analogs, templates = seed
    shape = shape_of(templates)
    anchor = anchor_from_result(analogs, shape)
    design = {"top_concentration_uM": shape.top_concentration_uM, "dilution_factor": shape.dilution_factor,
              "n_points": shape.n_points}
    ignored = check_series_consistent_with_analogs(design, analogs, citations=anchor.analog_ids,
                                                   query_compound=DEMO_COMPOUND)
    assert ignored.passed is False and "analog anchor" in ignored.reason
    anchored = check_series_consistent_with_analogs({**design, "top_concentration_uM": anchor.top_concentration_uM},
                                                    analogs, citations=anchor.analog_ids,
                                                    query_compound=DEMO_COMPOUND)
    assert anchored.passed, anchored.reason


def test_the_rule_in_the_protocol_graph_agrees(seed):
    from kg.protocols.build_db import check_rule, load_rules

    _, analogs, templates = seed
    rule = {r["id"]: r for r in load_rules()}["rule:agm/anchor_series_on_analogs"]
    shape = shape_of(templates)
    anchor = anchor_from_result(analogs, shape)
    base = {"assay_type": "biochemical kinase inhibition", "readout": "luminescence (ADP-Glo)",
            "system": "recombinant BTK kinase domain", "dilution_factor": shape.dilution_factor,
            "n_points": shape.n_points, "replicates": 3, "controls": ["DMSO vehicle", "no-enzyme wells"],
            **anchor.rule_context()}
    assert check_rule(rule, {**base, "top_concentration_uM": anchor.top_concentration_uM}) is True
    assert check_rule(rule, {**base, "top_concentration_uM": shape.top_concentration_uM}) is False
