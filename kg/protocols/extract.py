"""LLM extraction of one PubChem AID's protocol text into a structured template (pydantic, provenance per field).

    python -m kg.protocols.extract 623998                     # extract one AID (needs NEBIUS_API_KEY)
    python -m kg.protocols.extract 623998 --out kg/protocols/templates/draft_623998.json

From Python:

    from kg.protocols.extract import extract_aid, ExtractedProtocol
    protocol = extract_aid(623998)        # ExtractedProtocol, validated

The model sees the AID's name, description, protocol and comment text plus the tested concentration series, and
must answer with JSON only: ordered steps from a closed verb set, parameters with a value and a unit, controls, a
readout and a plate format. Every extracted field carries its provenance (the AID and a text span quoted from the
AID), so nothing in the graph is unattributable. Output is validated against the schema here; one retry with the
validation errors appended, then it raises.

Units are normalized in code, not by the model (`normalize`): uM for concentrations, min for times, uL for
volumes, C for temperatures. An unknown unit is kept as given and flagged in `unit_note`.

TODO(final): never run for real (no API key on the build machine). The unit tests drive it with a stubbed client;
the curated templates in templates/ were written by hand from the same AID text.
"""
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from kg.protocols.pubchem import PubChem
from wwtn.llm import chat

VERBS = ("prepare", "dispense", "serial_dilute", "add", "mix", "incubate", "detect", "read")
Verb = Literal["prepare", "dispense", "serial_dilute", "add", "mix", "incubate", "detect", "read"]

# (unit as written, lowercased) -> (canonical unit, factor). Concentrations to uM, times to min, volumes to uL.
UNITS = {
    "um": ("uM", 1.0), "µm": ("uM", 1.0), "micromolar": ("uM", 1.0), "umol/l": ("uM", 1.0),
    "nm": ("uM", 1e-3), "nanomolar": ("uM", 1e-3), "mm": ("uM", 1e3), "millimolar": ("uM", 1e3),
    "m": ("uM", 1e6), "pm": ("uM", 1e-6),
    "min": ("min", 1.0), "minute": ("min", 1.0), "minutes": ("min", 1.0), "mins": ("min", 1.0),
    "h": ("min", 60.0), "hr": ("min", 60.0), "hrs": ("min", 60.0), "hour": ("min", 60.0), "hours": ("min", 60.0),
    "s": ("min", 1 / 60), "sec": ("min", 1 / 60), "seconds": ("min", 1 / 60),
    "ul": ("uL", 1.0), "µl": ("uL", 1.0), "microliter": ("uL", 1.0), "microliters": ("uL", 1.0),
    "nl": ("uL", 1e-3), "ml": ("uL", 1e3), "l": ("uL", 1e6),
    "c": ("C", 1.0), "degrees c": ("C", 1.0), "celsius": ("C", 1.0),
}


class Provenance(BaseModel):
    """Where one extracted value comes from: the AID and the span of its text that says so."""
    aid: int
    field: Literal["name", "description", "protocol", "comment", "results"] = "protocol"
    quote: str = Field(min_length=3)   # must appear in that AID field: checked by `check_quotes`


class Parameter(BaseModel):
    name: str
    value: float | str
    unit: str | None = None
    unit_note: str | None = None       # set by `normalize` when a unit is not recognized
    provenance: Provenance


class Step(BaseModel):
    order: int = Field(ge=1)
    verb: Verb
    text: str
    parameters: list[str] = Field(default_factory=list)   # names of parameters this step sets
    provenance: Provenance


class Control(BaseModel):
    name: str
    role: Literal["negative", "positive", "counterscreen", "other"]
    provenance: Provenance


class ExtractedProtocol(BaseModel):
    aid: int
    archetype: str | None = None                   # a proto:... id when the caller knows which archetype it is
    assay_type: str
    readout: str
    system: str                                    # "recombinant GSK3beta", "Ba/F3 EpoR-JAK2V617F cells", ...
    plate_wells: int | None = None
    steps: list[Step] = Field(min_length=1)
    parameters: list[Parameter] = Field(default_factory=list)
    controls: list[Control] = Field(default_factory=list)
    provenance_note: str = ""

    def normalized(self) -> "ExtractedProtocol":
        return self.model_copy(update={"parameters": [normalize(p) for p in self.parameters]})


def normalize(parameter: Parameter) -> Parameter:
    """Convert a parameter to the canonical unit (uM, min, uL, C). Unknown units are kept and flagged."""
    if parameter.unit is None or not isinstance(parameter.value, (int, float)):
        return parameter
    known = UNITS.get(parameter.unit.strip().lower())
    if known is None:
        return parameter.model_copy(update={"unit_note": f"unrecognized unit {parameter.unit!r}, left as written"})
    unit, factor = known
    return parameter.model_copy(update={"value": float(parameter.value) * factor, "unit": unit})


SYSTEM = (
    "You extract one bioassay protocol into JSON. Use only what the given assay record says; never add typical or "
    "textbook values. Answer with a single JSON object and nothing else."
)

PROMPT = """Extract this PubChem BioAssay record into JSON with exactly these keys:

  "aid": {aid},
  "assay_type": short phrase, e.g. "biochemical kinase activity, luminescent ADP detection"
  "readout": what is measured, e.g. "luminescence (ADP-Glo)"
  "system": what the compound acts on, e.g. "recombinant GSK3beta" or "Ba/F3 EpoR-JAK2V617F cells"
  "plate_wells": integer well count of the assay plate, or null
  "steps": ordered list of {{"order": 1.., "verb": one of {verbs}, "text": one sentence,
           "parameters": [names of parameters this step sets],
           "provenance": {{"aid": {aid}, "field": "protocol"|"description"|"comment"|"name"|"results",
                           "quote": text copied verbatim from that field}}}}
  "parameters": list of {{"name": snake_case, "value": number or string, "unit": unit as written or null,
                          "provenance": as above}}
  "controls": list of {{"name": ..., "role": "negative"|"positive"|"counterscreen"|"other",
                        "provenance": as above}}

Rules: every quote must be copied exactly from the field it names. Do not convert units; give the value and the
unit as the record writes them. Omit anything the record does not state. One step per action.

--- AID {aid}: {name}
--- tested concentration series (from the results columns)
{series}
--- description
{description}
--- protocol
{protocol}
--- comment
{comment}
"""


def build_prompt(record: dict, limit: int = 6000) -> str:
    series = "\n".join(
        f"series {s['dr_id']}: {s['n_points']} points, top {s['top_uM']} uM"
        + (f", {s['dilution_factor']}-fold steps" if s["dilution_factor"] else ", irregular spacing")
        for s in record["series"]) or "none"
    return PROMPT.format(aid=record["aid"], name=record["name"], verbs=list(VERBS), series=series,
                         description=record["description"][:limit], protocol=record["protocol"][:limit],
                         comment=record["comment"][:limit])


def check_quotes(protocol: ExtractedProtocol, record: dict) -> list[str]:
    """Provenance quotes that do not appear in the AID field they name (whitespace-insensitive)."""
    squash = lambda s: " ".join(s.split())  # noqa: E731
    text = {f: squash(str(record.get(f, ""))) for f in ("name", "description", "protocol", "comment")}
    text["results"] = squash(json.dumps(record.get("series", [])))
    bad = []
    for item in [*protocol.steps, *protocol.parameters, *protocol.controls]:
        p = item.provenance
        if squash(p.quote) not in text.get(p.field, ""):
            bad.append(f"{type(item).__name__} {getattr(item, 'name', getattr(item, 'text', ''))[:40]!r}: "
                       f"quote not found in {p.field}: {p.quote[:60]!r}")
    return bad


def extract(record: dict, archetype: str | None = None, chat_fn=chat, **kwargs) -> ExtractedProtocol:
    """One extraction with one retry: invalid JSON, a schema error or a quote that is not in the record's text all
    go back to the model as the retry's complaint. `chat_fn` is wwtn.llm.chat (stubbed in the tests)."""
    prompt = build_prompt(record)
    complaint = None
    for attempt in range(2):
        messages = [{"role": "user", "content": prompt}]
        if complaint:
            messages.append({"role": "user", "content": f"That answer was rejected:\n{complaint}\nAnswer again, "
                                                        f"JSON only, fixing those problems."})
        answer = chat_fn(messages, system=SYSTEM, **kwargs)
        try:
            protocol = ExtractedProtocol.model_validate_json(_json_block(answer))
        except (ValidationError, ValueError) as err:
            complaint = str(err)[:2000]
            continue
        bad = check_quotes(protocol, record)
        if bad:
            complaint = "\n".join(bad)[:2000]
            continue
        return protocol.model_copy(update={
            "archetype": archetype or protocol.archetype,
            "provenance_note": f"LLM-extracted from PubChem AID {record['aid']}",
        }).normalized()
    raise ValueError(f"extraction of AID {record['aid']} failed twice: {complaint}")


def _json_block(answer: str) -> str:
    """The JSON object in a model answer, tolerating a ```json fence or text around it."""
    text = answer.strip()
    if "```" in text:
        text = text.split("```json")[-1].split("```")[-2] if "```json" in text else text.split("```")[1]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"no JSON object in the answer: {answer[:200]!r}")
    return text[start:end + 1]


def extract_aid(aid: int, archetype: str | None = None, **kwargs) -> ExtractedProtocol:
    return extract(PubChem().assay(aid), archetype=archetype, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one PubChem AID's protocol into the template schema.")
    parser.add_argument("aid", type=int)
    parser.add_argument("--archetype", help="the proto:... archetype this AID is an exemplar of")
    parser.add_argument("--out", type=Path, help="write the JSON here instead of stdout")
    args = parser.parse_args()
    protocol = extract_aid(args.aid, archetype=args.archetype)
    text = protocol.model_dump_json(indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
