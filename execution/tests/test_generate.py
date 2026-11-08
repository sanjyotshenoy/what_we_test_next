"""Proposals in, protocols out. The contract `wwtn/schema.py` already described and nobody had implemented.

`execution/examples/mic_selectivity.jsonl` is the end-to-end case that needs no API key: a hand-written
proposal for the four-species selectivity panel, which is also the only way to exercise this chain until
`NEBIUS_API_KEY` exists on a machine.
"""
import shutil
from pathlib import Path

import pytest

from execution.generate import generate, main
from execution.lab import Lab
from wwtn.schema import (ExecutionResult, Experiment, ExperimentProposal, PanelMember, read_jsonl,
                         write_jsonl)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "mic_selectivity.jsonl"


def test_the_example_proposal_is_the_agreed_panel_and_brackets_both_arms():
    proposal = read_jsonl(EXAMPLE, ExperimentProposal)[0]
    e = proposal.experiment
    assert [m.role for m in e.panel].count("pathogen") >= 2
    assert any(m.role == "commensal" for m in e.panel)
    assert all(m.reason for m in e.panel)                 # the panel is the answer; every choice is justified
    # 256 down by 2-fold over 10 points reaches 0.5: above the commensals' censored ">128" and below a
    # typical pathogen MIC, so one ladder covers both ends
    assert (e.top_concentration, e.concentration_unit) == (256.0, "ug/mL")
    assert e.top_concentration / e.dilution_factor ** (e.n_points - 1) == pytest.approx(0.5)
    assert len(e.panel) * e.replicates == 8               # exactly fills the plate's rows


def test_it_writes_a_protocol_a_run_sheet_and_a_result_per_proposal(tmp_path):
    results = generate(EXAMPLE, tmp_path, Lab.load())
    assert len(results) == 1
    result = results[0]
    assert Path(result.protocol_path).exists() and Path(result.run_sheet_path).exists()
    assert result.api_level
    # the results file is the contract benchmark/ reads
    assert read_jsonl(tmp_path / "results.jsonl", ExecutionResult)[0].question_id == result.question_id


def test_a_question_the_kb_already_answers_produces_nothing_to_run(tmp_path):
    answered = ExperimentProposal(question_id="q-known", answerable_from_kb=True,
                                  answer="Published: MIC 2 ug/mL.")
    write_jsonl(tmp_path / "in.jsonl", [answered])
    assert generate(tmp_path / "in.jsonl", tmp_path / "out", Lab.load()) == []


def test_an_infeasible_proposal_records_why_instead_of_a_protocol_that_would_fail(tmp_path):
    too_hot = ExperimentProposal(
        question_id="q-hot", answerable_from_kb=False,
        experiment=Experiment(assay_type="broth microdilution (MIC)", readout="absorbance 590 nm",
                              system="bacterial panel", top_concentration=64, concentration_unit="ug/mL",
                              dilution_factor=2, n_points=10, incubation_C=65,
                              panel=[PanelMember(name="Thermus thermophilus")]))
    write_jsonl(tmp_path / "in.jsonl", [too_hot])
    result = generate(tmp_path / "in.jsonl", tmp_path / "out", Lab.load())[0]
    assert result.protocol_path == "" and not result.simulated_ok
    assert "65" in result.error


def test_the_run_sheet_tells_the_person_which_atmosphere_to_incubate_in(tmp_path):
    results = generate(EXAMPLE, tmp_path, Lab.load())
    sheet = Path(results[0].run_sheet_path).read_text(encoding="utf-8")
    assert "incubate **anaerobic**" in sheet
    assert sheet.count("anaerobic incubation (jars") == 1      # said once, not three times
    assert "512 ug/mL" in sheet                                # the 2x prep


@pytest.mark.skipif(shutil.which("opentrons_simulate") is None,
                    reason="opentrons_simulate not on PATH (needs opentrons<=8.8.2 and numpy<2; see README)")
def test_the_whole_chain_runs_and_the_protocol_simulates(tmp_path, capsys):
    code = main([str(EXAMPLE), "--out", str(tmp_path), "--simulate"])
    assert code == 0
    assert "ok" in capsys.readouterr().out
    assert read_jsonl(tmp_path / "results.jsonl", ExecutionResult)[0].simulated_ok
