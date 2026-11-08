"""The shared contract: a panel of species, a concentration that knows its own unit, and old records that
still load. Every other folder reads these fields, so the back-compat cases here are not academic."""
import pytest

from wwtn.schema import Experiment, ExperimentProposal, PanelMember, PlateLayout

MIC = dict(assay_type="broth microdilution (MIC)", readout="absorbance 590 nm (turbidity)",
           system="bacterial panel", dilution_factor=2, n_points=10)


def test_a_ug_per_mL_experiment_has_no_micromolar_value():
    # the conversion needs a molecular weight this model does not have, so it must refuse rather than guess
    e = Experiment(**MIC, top_concentration=64, concentration_unit="ug/mL")
    assert e.top_concentration == 64 and e.concentration_unit == "ug/mL"
    assert e.top_concentration_uM is None


def test_micromolar_fills_both_fields():
    e = Experiment(**MIC, top_concentration=10, concentration_unit="uM")
    assert e.top_concentration_uM == 10


def test_nanomolar_converts_because_the_unit_is_the_same_quantity():
    e = Experiment(**MIC, top_concentration=500, concentration_unit="nM")
    assert e.top_concentration_uM == pytest.approx(0.5)


def test_an_explicit_unit_is_never_overwritten_by_the_legacy_field():
    # the regression this pair of fields exists to prevent: taking the value from top_concentration_uM used to
    # force the unit to uM with it, relabelling 256 ug/mL as 256 uM. agent/propose.py offers the model
    # top_concentration_uM and nothing else, so this is the shape it will emit the day it learns about units.
    e = Experiment(**MIC, concentration_unit="ug/mL", top_concentration_uM=256)
    assert (e.top_concentration, e.concentration_unit) == (256.0, "ug/mL")
    assert e.top_concentration_uM is None          # there is no micromolar value for a mass concentration


def test_an_explicit_micromolar_unit_still_round_trips():
    e = Experiment(**MIC, concentration_unit="nM", top_concentration_uM=500)
    assert (e.top_concentration, e.concentration_unit) == (500.0, "nM")
    assert e.top_concentration_uM == pytest.approx(0.5)


def test_a_record_written_against_the_old_schema_still_loads():
    # agent/anchor.py, the recorded demo traces and benchmark/ground_truth.jsonl all predate the unit field
    e = Experiment(**MIC, top_concentration_uM=12.0)
    assert (e.top_concentration, e.concentration_unit, e.top_concentration_uM) == (12.0, "uM", 12.0)


def test_the_panel_is_the_species_list_and_system_is_the_fallback():
    e = Experiment(**MIC, top_concentration=64, concentration_unit="ug/mL",
                   panel=[PanelMember(name="Bacteroides fragilis"), PanelMember(name="C. difficile")])
    assert e.species() == ["Bacteroides fragilis", "C. difficile"]
    assert Experiment(**{**MIC, "system": "recombinant KIT"}, top_concentration_uM=10).species() == \
        ["recombinant KIT"]


def test_a_panel_member_carries_why_it_is_on_the_plate():
    m = PanelMember(name="Bifidobacterium longum", id="CHEMBL613911", role="commensal",
                    oxygen_tolerance="strict anaerobe", reason="commensal arm; 243 MIC records in ChEMBL")
    assert m.role == "commensal" and m.reason
    assert PanelMember(name="x").role == "unknown"      # never silently labelled


def test_the_layout_defaults_to_the_teams_own_protocol():
    layout = PlateLayout()
    assert (layout.plate_format, layout.series_axis, layout.replicates_axis) == (96, "columns", "rows")
    assert len(layout.control_columns) == 2


def test_a_proposal_round_trips_through_json_with_the_panel_intact():
    e = Experiment(**MIC, top_concentration=64, concentration_unit="ug/mL",
                   panel=[PanelMember(name="C. difficile", role="pathogen")],
                   medium="CAMHB", incubation_C=37, incubation_h=18, atmosphere="anaerobic")
    proposal = ExperimentProposal(question_id="q1", answerable_from_kb=False, experiment=e)
    again = ExperimentProposal.model_validate_json(proposal.model_dump_json())
    assert again.experiment.panel[0].role == "pathogen"
    assert again.experiment.atmosphere == "anaerobic"
    assert again.experiment.top_concentration_uM is None
