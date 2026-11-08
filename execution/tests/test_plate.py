"""The plate design, and the audit that is supposed to catch it being wrong.

The audit only earns its keep if it disagrees with a broken map, so most of these break something on purpose.
"""
import pytest

from execution.lab import Lab
from execution.plate import GROWTH, STERILITY, audit, plate_design
from wwtn.schema import Experiment

PANEL = [{"id": "s1", "name": "S. aureus"}, {"id": "s2", "name": "E. coli"}]


def mic(**extra) -> Experiment:
    kwargs = dict(assay_type="broth microdilution", readout="turbidity (OD600)", system="panel",
                  top_concentration_uM=64, dilution_factor=2, n_points=10, replicates=1,
                  controls=[GROWTH, STERILITY])
    kwargs.update(extra)
    return Experiment(**kwargs)


@pytest.fixture(scope="module")
def lab() -> Lab:
    return Lab.load()


def test_the_series_halves_across_the_columns(lab):
    d = plate_design(mic(), lab, PANEL)
    row = [d.well(1, "A", c).final_uM for c in range(1, 11)]
    assert row[0] == 64 and row[-1] == pytest.approx(0.125)
    assert all(a == pytest.approx(b * 2) for a, b in zip(row, row[1:]))


def test_the_plate_holds_twice_what_the_cells_see(lab):
    """The 100+100 format: an equal volume of inoculum halves every concentration."""
    d = plate_design(mic(), lab, PANEL)
    w = d.well(1, "A", 1)
    assert w.final_uM == 64 and w.prepared_uM == 128
    assert any("2x" in n for n in d.notes)


def test_one_row_per_species_per_replicate(lab):
    d = plate_design(mic(replicates=3), lab, PANEL)
    assert {w.row for w in d.wells} == set("ABCDEF")          # 2 species x 3 replicates
    assert d.plates == 1
    assert [w.species for w in d.wells if w.column == 1] == ["S. aureus"] * 3 + ["E. coli"] * 3


def test_a_panel_too_big_for_one_plate_spills_over(lab):
    panel = [{"id": f"s{i}", "name": f"sp{i}"} for i in range(10)]
    d = plate_design(mic(), lab, panel)
    assert d.plates == 2
    assert {w.row for w in d.wells if w.plate == 2} == {"A", "B"}


def test_the_controls_are_what_they_claim(lab):
    d = plate_design(mic(), lab, PANEL)
    growth, sterility = d.well(1, "A", 11), d.well(1, "A", 12)
    assert growth.role == GROWTH and growth.final_uM == 0
    assert sterility.role == STERILITY and sterility.species is None   # no inoculum
    assert audit(d) == []


def test_a_series_longer_than_the_plate_is_truncated_and_said_so(lab):
    d = plate_design(mic(n_points=12), lab, PANEL)
    assert d.series_columns == 10
    assert any("truncated" in n for n in d.notes)


# --- the audit has to actually disagree ---------------------------------------------------------------------

def test_audit_catches_the_prepared_vs_final_confusion(lab):
    """The error that would silently double every reported MIC."""
    d = plate_design(mic(), lab, PANEL)
    w = d.well(1, "A", 1)
    w.final_uM = w.prepared_uM
    problems = audit(d)
    assert any("A1" in p and "replay gives 64" in p for p in problems)


def test_audit_catches_compound_in_the_growth_control(lab):
    d = plate_design(mic(), lab, PANEL)
    d.well(1, "A", 11).final_uM = 5.0
    assert any("growth control must hold no compound" in p for p in audit(d))


def test_audit_catches_inoculum_in_the_sterility_control(lab):
    d = plate_design(mic(), lab, PANEL)
    d.well(1, "A", 12).species = "S. aureus"
    assert any("sterility control must receive no inoculum" in p for p in audit(d))


def test_audit_catches_a_wrong_rung(lab):
    d = plate_design(mic(), lab, PANEL)
    d.well(1, "B", 5).final_uM = 99.0
    assert any("B5" in p for p in audit(d))


def test_a_clean_design_passes_the_audit_at_several_shapes(lab):
    for n_points, fold, replicates in ((10, 2, 1), (8, 2, 2), (10, 2, 4)):
        d = plate_design(mic(n_points=n_points, dilution_factor=fold, replicates=replicates), lab, PANEL)
        assert audit(d) == [], f"{n_points} points, {fold}-fold, n={replicates}: {audit(d)}"


def test_render_shows_the_controls(lab):
    text = plate_design(mic(), lab, PANEL).render()
    assert "GC" in text and "SC" in text and "S. aureus" in text and "64" in text
