"""LLM extraction with a stubbed client: schema validation, the retry, provenance checks, unit normalization."""
import json
from pathlib import Path

import pytest

from kg.protocols.extract import Parameter, Provenance, build_prompt, check_quotes, extract, normalize
from kg.protocols.pubchem import parse_description

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def record():
    return parse_description(json.loads((FIXTURES / "aid_623998_description.json").read_text()))


def answer(record, **overrides) -> str:
    """A well-formed model answer for the AID 623998 fixture."""
    quote = "Incubate at room temperature for 60 minutes."
    data = {
        "aid": record["aid"],
        "assay_type": "biochemical kinase activity, luminescent ADP detection",
        "readout": "luminescence (ADP-Glo)",
        "system": "recombinant GSK3beta",
        "plate_wells": 384,
        "steps": [{"order": 1, "verb": "incubate", "text": "Run the kinase reaction for 60 min at RT.",
                   "parameters": ["kinase_reaction_time"],
                   "provenance": {"aid": record["aid"], "field": "protocol", "quote": quote}}],
        "parameters": [{"name": "kinase_reaction_time", "value": 60, "unit": "minutes",
                        "provenance": {"aid": record["aid"], "field": "protocol", "quote": quote}}],
        "controls": [{"name": "neutral control wells", "role": "negative",
                      "provenance": {"aid": record["aid"], "field": "comment",
                                     "quote": "Neutral control wells (NC; n=168)"}}],
    }
    data.update(overrides)
    return json.dumps(data)


class Stub:
    """A chat stub: returns the queued answers in order and records the messages it was given."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, messages, system=None, **kwargs):
        self.calls.append(messages)
        return self.answers[len(self.calls) - 1]


def test_extract_validates_and_normalizes_units(record):
    stub = Stub(answer(record))
    protocol = extract(record, archetype="proto:kinase_biochem_lum", chat_fn=stub)
    assert len(stub.calls) == 1
    assert protocol.archetype == "proto:kinase_biochem_lum"
    assert protocol.provenance_note == "LLM-extracted from PubChem AID 623998"
    assert protocol.steps[0].verb == "incubate"
    assert (protocol.parameters[0].value, protocol.parameters[0].unit) == (60.0, "min")   # "minutes" -> min


def test_extract_accepts_a_fenced_answer(record):
    protocol = extract(record, chat_fn=Stub(f"Here it is:\n```json\n{answer(record)}\n```\n"))
    assert protocol.aid == 623998


def test_extract_retries_once_on_a_schema_error_then_succeeds(record):
    bad = json.dumps({"aid": record["aid"], "assay_type": "x", "readout": "y", "system": "z", "steps": []})
    stub = Stub(bad, answer(record))
    protocol = extract(record, chat_fn=stub)
    assert len(stub.calls) == 2
    assert "rejected" in stub.calls[1][-1]["content"]
    assert protocol.steps


def test_extract_rejects_a_quote_that_is_not_in_the_aid(record):
    invented = json.loads(answer(record))
    invented["parameters"][0]["provenance"]["quote"] = "Incubate for 90 minutes at 42 degrees C."
    stub = Stub(json.dumps(invented), json.dumps(invented))
    with pytest.raises(ValueError, match="failed twice"):
        extract(record, chat_fn=stub)
    assert len(stub.calls) == 2
    assert "quote not found" in stub.calls[1][-1]["content"]


def test_extract_gives_up_on_junk(record):
    with pytest.raises(ValueError):
        extract(record, chat_fn=Stub("I cannot help with that.", "still not JSON"))


def test_check_quotes_matches_across_whitespace(record):
    good = Parameter(name="t", value=60, unit="min", provenance=Provenance(
        aid=623998, field="protocol", quote="Incubate at room temperature\n  for 60 minutes."))
    assert check_quotes(type("P", (), {"steps": [], "parameters": [good], "controls": []})(), record) == []


def test_normalize_units():
    at = lambda value, unit: normalize(Parameter(  # noqa: E731
        name="x", value=value, unit=unit, provenance=Provenance(aid=1, quote="abc")))
    assert (at(100, "nM").value, at(100, "nM").unit) == (0.1, "uM")
    assert (at(2, "hrs").value, at(2, "hrs").unit) == (120.0, "min")
    assert (at(25, "nL").value, at(25, "nL").unit) == (0.025, "uL")
    assert at(37, "degrees C").unit == "C"
    odd = at(5, "CFU/mL")
    assert (odd.value, odd.unit) == (5, "CFU/mL") and "unrecognized" in odd.unit_note
    assert at("room temperature", None).value == "room temperature"


def test_prompt_carries_the_text_and_the_series(record):
    prompt = build_prompt(record)
    assert "Dispense 20 uL/well of KBAPE" in prompt
    assert "serial_dilute" in prompt                     # the closed verb set is in the prompt
    # the fixture keeps the first 12 concentration columns of AID 623998, which interleave two dilution series
    assert "12 points, top 0.6 uM, irregular spacing" in prompt
