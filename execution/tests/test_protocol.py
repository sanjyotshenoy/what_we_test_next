"""The last link: a plate map becomes a file the OT-2 accepts, and the half the robot cannot do becomes a
run sheet. The tests that matter here are the ones that catch a protocol which *looks* right: the tip count,
the deck, the API level, and the steps the template asks for that the generator does not perform."""
import json
import shutil
from pathlib import Path

import pytest

from execution.lab import Lab
from execution.plate import plate_design
from execution.protocol import (INOCULUM, MEDIUM, max_api_level, plan_ops, reservoir_plan, run_sheet,
                                simulate, tip_columns, to_ot2, unimplemented_steps, write_protocol)
from wwtn.schema import Experiment, PanelMember, PlateLayout

TEMPLATE = Path(__file__).resolve().parents[2] / "kg" / "protocols" / "templates" / "bacterial_mic_broth.json"


@pytest.fixture
def lab():
    return Lab.load()


def experiment(**overrides):
    fields = dict(assay_type="broth microdilution (MIC)", readout="absorbance 590 nm (turbidity)",
                  system="bacterial panel", top_concentration=64, concentration_unit="ug/mL",
                  dilution_factor=2, n_points=10, replicates=2, medium="CAMHB",
                  incubation_C=37, incubation_h=18, atmosphere="anaerobic", well_volume_uL=200,
                  panel=[PanelMember(name="Clostridioides difficile", role="pathogen",
                                     oxygen_tolerance="aerotolerant anaerobe"),
                         PanelMember(name="Bacteroides fragilis", role="pathobiont",
                                     oxygen_tolerance="aerotolerant anaerobe")])
    return Experiment(**{**fields, **overrides})


@pytest.fixture
def design(lab):
    return plate_design(experiment(), lab)


def test_the_series_is_one_command_per_column_in_the_order_the_robot_runs_it(design):
    ops = [op for op in plan_ops(design) if op.kind != "comment"]
    liquids = [op.liquid for op in ops]
    # broth first, then compound, then the carry, then the inoculum: a different order is a different experiment
    assert liquids.index(MEDIUM) < liquids.index("compound") < liquids.index("dilution")
    assert liquids.index("dilution") < liquids.index(INOCULUM)
    assert sum(1 for op in ops if op.liquid == "dilution") == design.series_columns   # 9 carries + 1 discard


def test_the_dilution_chain_keeps_one_tip_and_the_inoculum_takes_a_fresh_one(design):
    ops = plan_ops(design)
    chain = [op for op in ops if op.liquid == "dilution"]
    assert all(op.new_tip == "never" for op in chain)
    assert all(op.new_tip == "always" for op in ops if op.liquid == INOCULUM)


def test_the_tip_count_is_the_one_the_simulator_runs_out_at(design):
    # 1 column for the broth + 1 for the compound + 1 for the chain + one per inoculum column = 14 at 10 points
    assert tip_columns(plan_ops(design)) == 14


def test_more_tip_columns_than_one_rack_holds_loads_a_second_rack(design, lab):
    protocol = to_ot2(design, experiment(), lab)
    assert protocol.tipracks == 2
    assert [role for role in protocol.deck] == ["plate1", "tips1", "tips2", "reservoir"]
    assert protocol.deck["plate1"][0] == 1 and protocol.deck["reservoir"][0] == 4


def test_it_generates_at_the_level_the_simulator_can_check_not_the_one_lab_yaml_declares(design, lab):
    protocol = to_ot2(design, experiment(), lab)
    assert protocol.api_level == max_api_level()
    declared = lab.instrument("ot2")["api_level"]
    if declared > max_api_level():
        assert any("apiLevel" in w for w in protocol.warnings)
    assert f'"apiLevel": "{protocol.api_level}"' in protocol.code


def test_the_generated_file_loads_the_labware_lab_yaml_names(design, lab):
    code = to_ot2(design, experiment(), lab).code
    for load_name in ("corning_96_wellplate_360ul_flat", "opentrons_96_tiprack_300ul",
                      "usascientific_12_reservoir_22ml"):
        assert load_name in code
    assert "load_instrument('p300_multi', 'left'" in code
    assert "def run(protocol):" in code


def test_the_plate_map_travels_with_the_protocol_so_it_can_be_reviewed(design, lab):
    code = to_ot2(design, experiment(), lab).code
    assert "Clostridioides difficile" in code          # the map is in the module docstring
    assert "GC = growth control" in code


def test_a_plate_that_does_not_fit_the_deck_says_so_rather_than_generating_half_of_it(lab):
    big = experiment(panel=[PanelMember(name=f"species {i}") for i in range(40)], replicates=3)
    design = plate_design(big, lab)
    protocol = to_ot2(design, big, lab)
    assert design.plates > 4                                        # 120 rows is 15 plates
    assert any("need another run" in w for w in protocol.warnings)
    # and the code only touches the plates it actually loaded
    loaded = sum(1 for role in protocol.deck if role.startswith("plate"))
    assert loaded < design.plates
    assert "reservoir = protocol.load_labware" in protocol.code     # never the thing that gets dropped
    assert f"plate{loaded + 1} = " not in protocol.code


def test_the_reservoir_plan_includes_the_volume_the_tips_cannot_reach(design, lab):
    plan = reservoir_plan(design, plan_ops(design), lab)
    dead = lab.labware("reservoir")[0]["dead_mL"]
    bare = sum(op.volume_uL for op in plan_ops(design)
               if op.kind == "transfer" and op.liquid == MEDIUM) * design.rows / 1000
    assert plan[MEDIUM] == pytest.approx(bare + dead, abs=0.01)


def test_a_reservoir_channel_that_cannot_hold_the_medium_is_a_warning_not_a_surprise(lab):
    many = experiment(panel=[PanelMember(name=f"species {i}") for i in range(8)], replicates=1)
    protocol = to_ot2(plate_design(many, lab), many, lab)
    assert protocol.reservoir_mL[MEDIUM] > 0


def test_every_on_robot_step_the_mic_template_asks_for_is_performed():
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    design = plate_design(experiment(), Lab.load())
    assert unimplemented_steps(template, plan_ops(design)) == []


def test_a_template_whose_steps_we_do_not_implement_names_them(design):
    # the honest guard: this generator is the MIC sequence, and says so for anything else
    template = {"steps": [{"verb": "centrifuge", "text": "Spin the plate at 1000 x g."},
                          {"verb": "dispense", "text": "Dispense the substrate."},
                          {"verb": "incubate", "text": "Incubate 18 h."}]}
    missing = unimplemented_steps(template, plan_ops(design))
    assert missing == []           # centrifuge is not an on-robot verb we claim, incubate is off-robot
    template["steps"].append({"verb": "transfer", "text": "Transfer the lysate to a fresh plate."})
    assert any("transfer" in m for m in unimplemented_steps(template, plan_ops(design)))


def test_the_run_sheet_carries_the_steps_the_robot_cannot_do(design, lab):
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    sheet = run_sheet(design, experiment(), lab, template)
    assert "## After the robot" in sheet
    assert "incubate" in sheet.lower() and "read" in sheet.lower()
    assert "MIC" in sheet                                      # how to call the result
    assert "anaerobic incubation" in sheet                     # the assumption lab.yaml records
    assert "128 ug/mL" in sheet                                # the 2x prep, stated in the right unit


def test_the_run_sheet_states_the_reservoir_volumes_a_person_has_to_pour(design, lab):
    sheet = run_sheet(design, experiment(), lab)
    assert "reservoir channel 1" in sheet and "mL" in sheet


def test_write_protocol_puts_both_halves_on_disk(design, lab, tmp_path):
    written = write_protocol(design, tmp_path / "q001", experiment(), lab)
    assert Path(written["protocol"]).read_text(encoding="utf-8").startswith('"""Generated by')
    assert Path(written["run_sheet"]).read_text(encoding="utf-8").startswith("# Run sheet")
    assert written["api_level"] == max_api_level()


def test_a_design_that_fails_its_own_audit_is_reported_not_generated_over(design, lab):
    design.wells[0].final_uM = 999.0        # the kind of mistake audit() exists to catch
    protocol = to_ot2(design, experiment(), lab)
    assert any("does not survive its own audit" in w for w in protocol.warnings)


def test_a_row_wise_series_is_generated_as_column_wise_and_feasibility_objects(lab):
    # the generator is column-wise because the pipette is; feasibility.py is where that gets refused
    from execution.feasibility import check_feasible
    sideways = experiment(layout=PlateLayout(series_axis="rows"))
    verdict = check_feasible(sideways, lab)
    assert not verdict.feasible
    assert any("rows" in v for v in verdict.violations)


@pytest.mark.skipif(shutil.which("opentrons_simulate") is None,
                    reason="opentrons_simulate not on PATH (needs opentrons<=8.8.2 and numpy<2; see README)")
def test_the_generated_protocol_runs_in_the_simulator(design, lab, tmp_path):
    written = write_protocol(design, tmp_path, experiment(), lab)
    ok, output = simulate(written["protocol"])
    assert ok, output
    assert "Aspirating" in output and "Dropping tip" in output
