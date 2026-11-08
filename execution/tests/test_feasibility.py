"""The feasibility check: every violation it can raise, and the cases that must pass.

The point of these is that a verdict is arithmetic, so each one pins a number rather than a mood.
"""
import copy

import pytest

from execution.feasibility import check_feasible, feasible_panel_size
from execution.lab import Lab
from wwtn.schema import Experiment

AEROBE = [{"id": "s1", "name": "S. aureus", "atmosphere": "aerobic"},
          {"id": "s2", "name": "E. coli", "atmosphere": "aerobic"}]
ANAEROBE = {"id": "b1", "name": "B. fragilis", "atmosphere": "anaerobic"}


def mic(n_points=10, replicates=3, readout="turbidity (OD600)", **extra) -> Experiment:
    return Experiment(assay_type="broth microdilution", readout=readout, system="bacterial panel",
                      top_concentration_uM=64, dilution_factor=2, n_points=n_points, replicates=replicates,
                      controls=["growth control", "sterility control"], **extra)


@pytest.fixture(scope="module")
def lab() -> Lab:
    return Lab.load()


def test_a_small_aerobic_panel_is_runnable(lab):
    v = check_feasible(mic(), lab, panel=AEROBE)
    assert v.feasible, v.sentence()
    assert v.columns_needed == 12                 # 10 concentrations + growth + sterility
    assert v.rows_needed == 6                     # 2 species x 3 replicates
    assert v.plates_needed == 1


def only(lab: Lab, *atmospheres: str) -> Lab:
    """The same lab with its atmosphere replaced, so the check can be tested in both directions whatever
    lab.yaml currently claims."""
    spec = copy.deepcopy(lab.spec)
    spec["capabilities"]["atmosphere"] = list(atmospheres)
    return Lab(spec)


def test_an_anaerobe_in_an_aerobic_lab_is_refused(lab):
    v = check_feasible(mic(), only(lab, "aerobic"), panel=[*AEROBE, ANAEROBE])
    assert not v.feasible
    assert any("B. fragilis" in x and "anaerobic" in x for x in v.violations)
    assert any("M11" in s or "agar dilution" in s for s in v.suggestions)


def test_an_obligate_aerobe_in_a_chamber_is_refused_too(lab):
    """The check runs both ways: P. aeruginosa is an obligate aerobe, so an anaerobic-only setup fails it."""
    panel = [{"id": "p1", "name": "P. aeruginosa", "atmosphere": "aerobic"}, ANAEROBE]
    v = check_feasible(mic(), only(lab, "anaerobic"), panel=panel)
    assert not v.feasible
    assert any("P. aeruginosa" in x for x in v.violations)
    assert not any("B. fragilis" in x for x in v.violations)


def test_a_facultative_species_runs_either_way(lab):
    panel = [{"id": "e1", "name": "E. coli", "atmosphere": "facultative"}]
    assert check_feasible(mic(), only(lab, "aerobic"), panel=panel).feasible
    assert check_feasible(mic(), only(lab, "anaerobic"), panel=panel).feasible


def test_the_assumed_chamber_is_reported_in_every_verdict(lab):
    """lab.yaml currently claims anaerobic as an ASSUMPTION; no verdict may hide that."""
    v = check_feasible(mic(), lab, panel=[*AEROBE, ANAEROBE])
    assert v.feasible
    assert any("ASSUMED" in w for w in v.warnings)


def test_too_many_concentrations_for_the_plate(lab):
    v = check_feasible(mic(n_points=13), lab, panel=AEROBE)
    assert not v.feasible
    assert any("more than the plate's 12" in x for x in v.violations)


def test_a_panel_that_needs_more_plates_says_how_many(lab):
    panel = [{"id": f"s{i}", "atmosphere": "aerobic"} for i in range(12)]
    v = check_feasible(mic(replicates=3), lab, panel=panel)
    assert v.rows_needed == 36 and v.plates_needed == 5    # 36 rows over 8-row plates
    assert any("2 species would fit on one" in s for s in v.suggestions)


def test_replication_is_the_trade_off(lab):
    assert feasible_panel_size(lab, replicates=8) == 1     # Emmy's layout: one strain, 8 replicates
    assert feasible_panel_size(lab, replicates=1) == 8     # or 8 species, no replication
    assert feasible_panel_size(lab, replicates=2, plates=2) == 8


def test_an_unreadable_readout_is_refused(lab):
    v = check_feasible(mic(readout="X-ray diffraction"), lab, panel=AEROBE)
    assert any("could not tell which reader mode" in w for w in v.warnings)


def test_a_temperature_we_cannot_reach_is_refused(lab):
    v = check_feasible(mic(), lab, panel=AEROBE)
    assert v.feasible
    v = check_feasible({"n_points": 10, "replicates": 3, "readout": "turbidity",
                        "incubation_C": 65}, lab, panel=AEROBE)
    assert not v.feasible
    assert any("65" in x for x in v.violations)


def test_unconfirmed_hardware_is_reported_not_assumed(lab):
    v = check_feasible(mic(), lab, panel=AEROBE)
    assert any("p20" in w.lower() for w in v.warnings)     # the right-hand pipette is unconfirmed in lab.yaml
    assert all(p.get("mounted") != "unconfirmed" for p in lab.pipettes())


def test_a_dict_experiment_works_too(lab):
    v = check_feasible({"n_points": 10, "replicates": 3, "readout": "turbidity (OD600)"}, lab, panel=AEROBE)
    assert v.feasible
