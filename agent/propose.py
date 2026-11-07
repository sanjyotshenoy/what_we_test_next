"""Aim 1: given a Question the knowledge base cannot answer, propose the missing experiment.

    python -m agent.propose --question "Does imatinib inhibit the KIT kinase, and how potently?"
    python -m agent.propose --questions benchmark/questions.jsonl --out agent/out/kg.jsonl
    python -m agent.propose --question "..." --runs-js demo/runs   # a trace for the demo page

The agent is a tool-calling loop on the LLM (wwtn.llm.chat_raw): it resolves the entities in the biology KG,
pulls analogs with measured activity to set the concentration range, fetches a protocol template for the target
class, and ends by calling `propose_experiment`. Every tool call, the model's reasoning between calls, and the
proposal go into a Trace (agent/trace.py), which is what the demo page plays.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from wwtn.llm import DEFAULT_MODEL, chat_raw, message_dict, reasoning_of
from wwtn.schema import Experiment, ExperimentProposal, Question, read_jsonl, write_jsonl

from .tools import TOOL_SPECS, KnowledgeBase
from .trace import Trace, slug

MAX_ROUNDS = 8
TIMEOUT = 120   # seconds per LLM call

SYSTEM = """You are the experiment-design agent of a biology lab. The knowledge base has already been asked \
the question and found no measurement for it, so your job is to propose the experiment that would answer it, \
grounded ONLY in what the tools return. Never present an IC50 from memory as a fact: the point is that this \
measurement does not exist yet.

Work in this order, one tool call at a time:
1. bio_kg_resolve: the compound, the target and the target's class.
2. bio_kg_analogs: similar compounds with measured activity on the target; their IC50s set the expected potency.
3. protocol_kg_templates: the protocol template for this question type and target class (format, readout, \
controls, default series).
4. propose_experiment, exactly once, with the final design.

Before each tool call, write ONE sentence of visible reasoning (at most 25 words): the key fact from the last \
result and what you do next; never restate a table. The concentration series must bracket the expected potency \
with at least two points on each side and reach a top plateau; derive the top concentration, dilution factor \
and number of points from the analog IC50s. Use the template's controls and replicates unless there is a reason \
not to. Keep every field of the proposal a short label (under 10 words); IDs go in `citations`, the node IDs \
you relied on (compound, target, analogs, protocol, format, endpoint), not in the field values."""

PROPOSE_SPEC = {"type": "function", "function": {
    "name": "propose_experiment",
    "description": "Submit the final experiment design. Call it once, after the graph tools.",
    "parameters": {"type": "object", "properties": {
        "assay_type": {"type": "string", "description": "e.g. biochemical kinase inhibition (dose-response); BAO terms where possible"},
        "readout": {"type": "string", "description": "e.g. luminescence (ADP formed)"},
        "system": {"type": "string", "description": "e.g. recombinant KIT kinase domain"},
        "top_concentration_uM": {"type": "number"},
        "dilution_factor": {"type": "number", "description": "3 for a 1:3 series"},
        "n_points": {"type": "integer"},
        "replicates": {"type": "integer"},
        "controls": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string", "description": "at most two short sentences (40 words): why this series and format answer the question; do not repeat the field values"},
        "citations": {"type": "array", "items": {"type": "string"}, "description": "KG node IDs relied on"}},
        "required": ["assay_type", "readout", "system", "top_concentration_uM", "dilution_factor", "n_points",
                     "replicates", "controls", "rationale", "citations"]}}}


def brief(thinking: str, sentences: int = 2, limit: int = 240) -> str:
    """The first sentences of a model's raw thinking, for models that give no visible text with a tool call."""
    parts = re.split(r"(?<=[.!?])\s+", thinking.strip())
    text = " ".join(parts[:sentences])
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def entities(question: Question, kb: KnowledgeBase, model: str) -> tuple[str, str]:
    """The compound and target the question is about: from the Question's fields, else matched against the
    KG's node names, else extracted by the model."""
    if question.compound and question.target:
        return question.compound, question.target
    text = question.text.lower()
    comp = next((n["name"] for n in kb.bio.nodes.values() if n["type"] == "Compound" and n["name"].lower() in text), None)
    targ = next((n["props"].get("gene") or n["name"] for n in kb.bio.nodes.values() if n["type"] == "Target"
                 and (str(n["props"].get("gene", "")).lower() in text.split() if n["props"].get("gene") else n["name"].lower() in text)), None)
    if comp and targ:
        return question.compound or comp, question.target or targ
    m = chat_raw(f"Question: {question.text}\nReply with JSON only: {{\"compound\": ..., \"target\": ...}} "
                 "(names as written; null if absent).", model=model, temperature=0, timeout=TIMEOUT)
    try:
        d = json.loads((m.content or "").strip().strip("`").removeprefix("json"))
    except json.JSONDecodeError:
        d = {}
    return question.compound or comp or d.get("compound") or "", question.target or targ or d.get("target") or ""


def propose(question: Question, model: str | None = None, kb: KnowledgeBase | None = None,
            trace: Trace | None = None, log=None) -> tuple[ExperimentProposal, Trace]:
    """Run the agent on one question. Returns the proposal and the trace of how it got there."""
    model = model or DEFAULT_MODEL
    kb = kb or KnowledgeBase()
    note = "Graphs: hand-written sample (agent/data/sample_kg)" if kb.sample else ""   # TODO(final): goes away with kg/*/graph
    trace = trace or Trace(question.id, question.text, model, note=note)
    say = log or (lambda *a: None)

    # 1. what the KB says on its own
    compound, target = entities(question, kb, model)
    lookup = kb.lookup(compound, target)
    found = lookup.pop("found")
    answer = lookup.pop("answer", None)
    lookup["note"] = ("The knowledge base already holds this measurement, so no experiment is needed." if found else
                      "No measurement for this pair in the knowledge base: the agent must propose the experiment, not the answer.")
    trace.set_lookup(lookup)
    say("lookup", lookup["verdict"], "·", lookup["result"])
    if found:
        trace.add_reasoning("The knowledge base answers this directly; no experiment is needed.")
        proposal = ExperimentProposal(question_id=question.id, answerable_from_kb=True, answer=lookup["result"],
                                      rationale="Answered from the knowledge base.", citations=[r[0] for r in lookup["rows"]] + [r[2] for r in lookup["rows"]],
                                      model=model)
        trace.set_proposal(proposal.model_dump())
        trace.done()
        return proposal, trace

    # 2–4. the tool-calling loop
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Question: {question.text}\nCompound: {compound}\nTarget: {target}\n"
                                            f"The knowledge base says: {lookup['result']}"}]
    proposal = None
    for _ in range(MAX_ROUNDS):
        m = chat_raw(messages, model=model, tools=TOOL_SPECS + [PROPOSE_SPEC], temperature=0.2, timeout=TIMEOUT)
        messages.append(message_dict(m))
        text, thinking = (m.content or "").strip(), reasoning_of(m)
        if text or thinking:
            shown = text or brief(thinking)
            trace.add_reasoning(shown, thinking)
            say("reasoning", shown[:160].replace("\n", " "))
        if not m.tool_calls:
            messages.append({"role": "user", "content": "Continue: call the next tool, or propose_experiment if you have what you need."})
            continue
        for tc in m.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "propose_experiment":
                try:
                    experiment = Experiment(**{k: args[k] for k in Experiment.model_fields if k in args})
                except Exception as e:   # pydantic ValidationError: tell the model and let it retry
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Rejected: {e}. Call propose_experiment again with valid fields."})
                    say("proposal rejected", str(e)[:160])
                    continue
                proposal = ExperimentProposal(question_id=question.id, answerable_from_kb=False, experiment=experiment,
                                              rationale=args.get("rationale", ""), citations=[str(c) for c in args.get("citations", [])],
                                              model=model)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": "Recorded."})
                if proposal.rationale:
                    trace.add_reasoning(proposal.rationale)
                trace.set_proposal(proposal.model_dump())
                say("proposal", experiment.assay_type, "·", f"{experiment.top_concentration_uM} µM top, 1:{experiment.dilution_factor}, {experiment.n_points} points")
                break
            result = kb.call(name, args)
            trace.add_call({"tool": name.replace("_kg_", "_kg.", 1), "args": args, "summary": result.get("summary", ""),
                            "rows": result.get("rows", []), **({"columns": result["columns"]} if result.get("columns") else {})})
            say("call", name, json.dumps(args), "→", result.get("summary", ""))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": kb.result_text(result)})
        if proposal:
            break
    if not proposal:
        trace.fail(f"No proposal after {MAX_ROUNDS} rounds.")
        raise RuntimeError(f"{question.id}: the model did not call propose_experiment within {MAX_ROUNDS} rounds")
    trace.done()
    return proposal, trace


def main() -> None:
    ap = argparse.ArgumentParser(description="Propose the experiment that would answer a question the KB cannot.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--question", help="one question, as text")
    src.add_argument("--questions", help="a Question JSON Lines file (benchmark/questions.jsonl)")
    ap.add_argument("--id", help="run/question ID for --question (default: from the text)")
    ap.add_argument("--model", help=f"model ID (default: {DEFAULT_MODEL})")
    ap.add_argument("--kg", help="folder holding biology/graph and protocols/graph (default: kg/)")
    ap.add_argument("--out", help="ExperimentProposal JSON Lines to write (default: agent/out/<model>.jsonl)")
    ap.add_argument("--traces", default="agent/out/traces", help="folder for <id>.json traces")
    ap.add_argument("--runs-js", help="also write each trace as <folder>/<id>.js for the demo page")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    questions = (read_jsonl(a.questions, Question) if a.questions else
                 [Question(id=a.id or slug(a.question), text=a.question)])
    model = a.model or DEFAULT_MODEL
    kb = KnowledgeBase(a.kg)
    log = (lambda *x: None) if a.quiet else (lambda *x: print(*x, file=sys.stderr, flush=True))
    log("model:", model, "· graphs:", kb.source)

    proposals = []
    for q in questions:
        log(f"\n== {q.id}: {q.text}")
        proposal, trace = propose(q, model=model, kb=kb, log=log)
        proposals.append(proposal)
        p = trace.write_json(Path(a.traces) / f"{q.id}.json")
        log("trace:", p)
        if a.runs_js:
            log("demo trace:", trace.write_js(Path(a.runs_js) / f"{q.id}.js"))
    out = a.out or f"agent/out/{slug(model)}.jsonl"
    write_jsonl(out, proposals)
    log("proposals:", out)


if __name__ == "__main__":
    main()
