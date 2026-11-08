"""The anchor in the trace and in the propose loop: additive trace fields (demo/README.md is a contract), and
the model following or departing from the anchor with a stated reason."""
import pytest

from wwtn.schema import Question

from agent import propose as propose_mod
from agent.anchor import Shape, anchor_from_analogs
from agent.tests.test_propose_stub import FINAL, FakeMessage, FakeToolCall
from agent.trace import Trace

KINASE = Shape(dilution_factor=3.0, n_points=10, top_concentration_uM=10.0)


@pytest.fixture()
def script(monkeypatch):
    """Replay a list of FakeMessages (the same stub as test_propose_stub.py: no API key, no network)."""
    def install(messages):
        sent = []

        def fake_chat_raw(prompt, **kwargs):
            sent.append(prompt)
            return messages[min(len(sent) - 1, len(messages) - 1)]

        monkeypatch.setattr(propose_mod, "chat_raw", fake_chat_raw)
        return sent
    return install


def steps(*tool_calls):
    """The stub's script: resolve, analogs, templates, then propose_experiment with these args."""
    return [
        FakeMessage("Resolving.", [FakeToolCall("bio_kg_resolve", {"compound": "CAND1", "target": "P00001"})]),
        FakeMessage("Analogs.", [FakeToolCall("bio_kg_analogs", {"compound": "CAND1", "target": "P00001"})]),
        FakeMessage("Template.", [FakeToolCall("protocol_kg_templates",
                                               {"question_type": "potency", "target": "P00001"})]),
        *tool_calls,
    ]


def run(kb, script, **final):
    args = {**FINAL, **final}
    script(steps(FakeMessage("Proposing.", [FakeToolCall("propose_experiment", args)])))
    question = Question(id="t-anchor", text="Does CAND1 inhibit test kinase one?",
                        compound="CAND1", target="P00001")
    return propose_mod.propose(question, model="stub", kb=kb)


# --- the trace fields ----------------------------------------------------------------------------------------

def test_the_trace_records_the_anchor_and_its_derivation():
    trace = Trace("t1", "q", "stub")
    assert "anchor" not in trace.to_dict()                 # absent until one is computed: nothing renamed
    anchor = anchor_from_analogs([{"compound": "C1", "ic50_nM": 8.2, "similarity": 0.6}], KINASE)
    trace.set_anchor(anchor.to_dict())
    recorded = trace.to_dict()["anchor"]
    assert recorded["top_concentration_uM"] == anchor.top_concentration_uM
    assert recorded["median_ic50_nM"] == 8.2 and recorded["multiplier_basis"]
    assert [a["compound"] for a in recorded["analogs"]] == ["C1"]
    assert recorded["confidence"] == "low" and recorded["flags"] == ["single_analog"]
    assert recorded["series_uM"] and recorded["agm"]["nbk"] == "NBK92007"


def test_the_trace_is_additive_and_json_safe():
    trace = Trace("t2", "q", "stub")
    trace.set_anchor(anchor_from_analogs([{"compound": "C1", "ic50_nM": 8.2}], KINASE).to_dict())
    data = trace.to_dict()
    assert set(data) >= {"id", "query", "model", "anchor"}
    assert "anchor" in trace.to_js() and "DEMO_RUNS" in trace.to_js()   # the page's format still parses
    events = []
    trace.on(lambda event, payload: events.append(event))
    trace.set_anchor_outcome(True, "")
    assert events == ["anchor"]                            # listeners (the live server) see it too


def test_the_outcome_records_a_departure_with_its_reason():
    trace = Trace("t3", "q", "stub")
    trace.set_anchor(anchor_from_analogs([{"compound": "C1", "ic50_nM": 8.2}], KINASE).to_dict())
    trace.set_anchor_outcome(False, "capped at the solubility limit", stated_top_uM=30.0,
                             stated_analogs=["C1"])
    anchor = trace.to_dict()["anchor"]
    assert anchor["followed"] is False and anchor["departure_reason"] == "capped at the solubility limit"
    assert anchor["stated_top_uM"] == 30.0 and anchor["stated_analogs"] == ["C1"]
    assert anchor["top_concentration_uM"]                  # the derivation is still there, not overwritten


# --- in the loop ---------------------------------------------------------------------------------------------

def test_the_loop_computes_the_anchor_and_hands_it_to_the_model(kb, script):
    sent = script(steps(FakeMessage("Proposing.", [FakeToolCall("propose_experiment", FINAL)])))
    question = Question(id="t4", text="Does CAND1 inhibit test kinase one?", compound="CAND1", target="P00001")
    _, trace = propose_mod.propose(question, model="stub", kb=kb)
    anchor = trace.to_dict()["anchor"]
    assert anchor["applicable"] is True and anchor["median_ic50_nM"] == 50.0   # 200, 50, 5 nM
    assert {a["compound"] for a in anchor["analogs"]} == {"CMP_A", "CMP_B", "CMP_OUT"}
    tool_messages = [m for m in sent[-1] if m.get("role") == "tool"]
    assert any("Analog anchor" in str(m["content"]) for m in tool_messages)


def test_the_system_prompt_makes_the_anchor_a_default_not_a_constraint():
    prompt = propose_mod.SYSTEM
    assert "anchor_top_uM" in prompt and "anchor_analogs" in prompt
    assert "DEFAULT, not a constraint" in prompt and "anchor_departure_reason" in prompt
    spec = propose_mod.PROPOSE_SPEC["function"]["parameters"]
    assert {"anchor_top_uM", "anchor_analogs", "anchor_departure_reason"} <= set(spec["properties"])
    assert not {"anchor_top_uM", "anchor_analogs", "anchor_departure_reason"} & set(spec["required"])


def test_a_proposal_on_the_anchor_is_recorded_as_followed(kb, script):
    _, trace = run(kb, script, top_concentration_uM=7.01, anchor_top_uM=7.01,
                   anchor_analogs=["CMP_A", "CMP_B", "CMP_OUT"])
    anchor = trace.to_dict()["anchor"]
    assert anchor["followed"] is True and "departure_reason" not in anchor
    assert anchor["stated_analogs"] == ["CMP_A", "CMP_B", "CMP_OUT"]


def test_a_departure_is_recorded_with_the_models_reason_not_corrected(kb, script):
    proposal, trace = run(kb, script, top_concentration_uM=100.0, anchor_top_uM=7.01,
                          anchor_analogs=["CMP_A"],
                          anchor_departure_reason="the compound precipitates below 100 uM")
    anchor = trace.to_dict()["anchor"]
    assert anchor["followed"] is False
    assert anchor["departure_reason"] == "the compound precipitates below 100 uM"
    # the proposal keeps the model's own number: the anchor is a default, not an override
    assert proposal.experiment.top_concentration_uM == 100.0
    assert anchor["top_concentration_uM"] == 7.01


def test_a_pair_the_kb_answers_records_no_anchor(kb, script):
    script([FakeMessage("", [])])
    question = Question(id="t5", text="Does analog-a inhibit test kinase two?", compound="CMP_A",
                        target="P00002")
    _, trace = propose_mod.propose(question, model="stub", kb=kb)
    assert "anchor" not in trace.to_dict()     # no experiment, no series, nothing to anchor
