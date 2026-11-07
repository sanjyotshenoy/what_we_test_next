"""The propose loop against a stubbed LLM client: no network, no API key. The stub plays the tool calls the
SYSTEM prompt asks for, so this checks the wiring (tool dispatch, the trace, the proposal) and not the model."""
import json

import pytest

from wwtn.schema import Question

from agent import propose as propose_mod
from agent.tools import DEMO_QUESTION


class FakeToolCall:
    def __init__(self, name, args, id="call-1"):
        self.id = id
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args)})()


class FakeMessage:
    """Enough of an openai ChatCompletionMessage for propose.py (`message_dict`, `reasoning_of`)."""

    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.model_extra = {}

    def model_dump(self, exclude_none=False):
        return {"role": "assistant", "content": self.content,
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name, "arguments": c.function.arguments}}
                               for c in self.tool_calls]}


@pytest.fixture()
def script(monkeypatch):
    """Replay a list of FakeMessages, recording the messages the loop sends."""
    def install(messages):
        sent = []

        def fake_chat_raw(prompt, **kwargs):
            sent.append(prompt)
            return messages[min(len(sent) - 1, len(messages) - 1)]

        monkeypatch.setattr(propose_mod, "chat_raw", fake_chat_raw)
        return sent
    return install


FINAL = {"assay_type": "biochemical kinase inhibition", "readout": "luminescence (ADP)",
         "system": "recombinant kinase", "top_concentration_uM": 10, "dilution_factor": 3, "n_points": 10,
         "replicates": 3, "controls": ["DMSO vehicle", "staurosporine"],
         "rationale": "Analogs sit at 50-300 nM, so a 1:3 series from 10 uM brackets them.",
         "citations": ["CAND1", "P00001", "proto:biochem"]}


def test_the_loop_runs_the_graph_tools_and_records_a_trace(kb, script):
    sent = script([
        FakeMessage("Resolving the pair.", [FakeToolCall("bio_kg_resolve", {"compound": "CAND1", "target": "P00001"})]),
        FakeMessage("Now the analogs.", [FakeToolCall("bio_kg_analogs", {"compound": "CAND1", "target": "P00001"})]),
        FakeMessage("Now a template.", [FakeToolCall("protocol_kg_templates",
                                                     {"question_type": "potency", "target": "P00001"})]),
        FakeMessage("Proposing.", [FakeToolCall("propose_experiment", FINAL)]),
    ])
    question = Question(id="t1", text="Does CAND1 inhibit test kinase one?", compound="CAND1", target="P00001")
    proposal, trace = propose_mod.propose(question, model="stub", kb=kb)

    assert proposal.answerable_from_kb is False
    assert proposal.experiment.n_points == 10 and proposal.citations == FINAL["citations"]
    # the trace keeps the field names the demo page and the demo repo read (demo/README.md)
    data = trace.to_dict()
    assert [c["tool"] for c in data["calls"]] == ["bio_kg.resolve", "bio_kg.analogs", "protocol_kg.templates"]
    for call in data["calls"]:
        assert set(call) >= {"tool", "args", "summary", "rows"}
    assert data["lookup"]["verdict"] == "I don’t know"
    assert data["plate"]["points"] == 10 and data["plate"]["top_uM"] == 10
    assert sent, "the stub was called"
    # the tool results the model saw carry the real graph rows
    tool_messages = [m for m in sent[-1] if m.get("role") == "tool"]
    assert any("Tanimoto" in str(m["content"]) for m in tool_messages)
    assert any("proto:biochem" in str(m["content"]) for m in tool_messages)


def test_a_pair_the_kb_already_answers_needs_no_experiment(kb, script):
    script([FakeMessage("", [])])
    question = Question(id="t2", text="Does analog-a inhibit test kinase two?", compound="CMP_A", target="P00002")
    proposal, trace = propose_mod.propose(question, model="stub", kb=kb)
    assert proposal.answerable_from_kb is True and proposal.experiment is None
    assert "IC50" in (proposal.answer or "")
    assert trace.to_dict()["lookup"]["verdict"] == "answered"


def test_entities_come_from_the_graph_without_an_llm(kb, script):
    """A question with no compound/target fields: kb.mentions() matches the text against the graph, so the
    extraction fallback never has to call the model."""
    script([FakeMessage("", [])])   # would raise IndexError only if the loop asked the model for entities
    assert propose_mod.entities(Question(id="t3", text="Is CAND1 active on Test kinase one?"), kb, "stub") == \
        ("CAND1", "Test kinase one")


def test_the_demo_question_names_a_pair_in_the_seed_graph():
    assert "CHEMBL5593141" in DEMO_QUESTION and "BTK" in DEMO_QUESTION
