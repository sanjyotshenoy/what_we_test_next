# Before we present

Everything mock, placeholder or unconfirmed is tagged `TODO(final)` where it lives. The live list is always:

```bash
grep -rn "TODO(final)" --exclude-dir=.git .
```

When you leave something fake or unfinished behind, add a `TODO(final): ...` comment at that spot; when you fix
it, delete the comment. The checklist below is a snapshot for orientation; the grep is the source of truth.

**On screen (embarrassing if forgotten)**
- [ ] Demo: `demo/runs/kit-imatinib.js` is a real agent run but against the hand-written sample graphs
  (`agent/data/sample_kg`); rerun it against `kg/*/graph` once they exist. The mock `demo/runs/kit_imatinib.js`
  stays until `execution/` and `benchmark/` feed the trace (procedure, protocol, simulation, validation), then
  drop it (also `demo/index.html`, `slides/talks/biohack/slides/demo.js` notes)
- [ ] Benchmark charts are empty ("—"): fill `RESULTS` in `slides/talks/biohack/slides/benchmarks.js`
- [ ] Slides that still say "Placeholder: ...": `slides/talks/biohack/slides/blank.js`
- [ ] Outline is the dummy one: confirm `slides/talks/biohack/slides/outline.js`
- [ ] Title slide photo for Jimmy Hsu: `slides/talks/biohack/slides/title.js`

**Behind the scenes**
- [ ] Confirm the four benchmark models are live on our key: `wwtn/llm.py` and `benchmarks.js`
- [ ] Pick the range-accuracy metric before writing the grader: `benchmark/README.md`
- [ ] Owners in each folder README: `agent/`, `execution/`, `benchmark/`, `kg/biology/`, `kg/protocols/`
- [ ] `agent/`: baselines (bare LLM, LLM + literature search) for a fair comparison; delete `agent/data/sample_kg`

## Pipeline gaps (2026-11-07 19:20; not yet built or decided)

**LLM orchestration**
- [ ] Agent loop: a first tool-calling loop exists (`agent/propose.py`, `agent/tools.py`, PR #1) on the sample
  graphs; still to do: switch its tools to `kg/query.py`, check which Nebius models support function calling
  (JSON-action fallback otherwise)
- [ ] Step 1, "can the KB answer this?": the abstain/answer decision (what it queries, criteria, prompt)
- [ ] Literature-search tool for the "+lit" arm (Europe PMC? Paperclip?), **date-filtered to the cutoff** so it
  cannot find the held-out paper
- [ ] Similarity tool: RDKit analogs on the same target live in `agent/kg_backend.py` (Morgan r2, 2048 bits,
      Tanimoto, same-target IC50s); move them into `kg/query.py` if other folders need them
- [ ] Agent demo question: `CHEMBL5593141` x BTK (`agent/tools.py`, `DEMO_COMPOUND`/`DEMO_TARGET`) is a
      stand-in chosen by analog support; confirm with Seh Na's candidate list
- [ ] Gene symbols for the 19 seed kinases are hard-coded in `agent/kg_backend.py` (`GENES`); they belong on the
      Target nodes, from UniProt, in `kg/biology/build_seed.py`
- [ ] Decide: range from priors + AGM rules deterministically, or by the LLM
- [ ] Structured output: `ExperimentProposal` via pydantic, retry on invalid JSON, citation validator (IDs must
  appear in tool results)
- [ ] The three arms with equal budgets: bare / + literature / + KGs
- [ ] Run harness: models × arms × questions, retries, rate limits, caching, token/cost logging, temperature/seed,
  run IDs, trace logging (feeds the grader and the demo)

**Execution (aim 2)**
- [ ] Proposal → hardware-agnostic procedure JSON → plate design; `execution/lab.yaml` inventory
- [ ] OT-2 code generation: template baseline + LLM loop with simulator feedback (≤ 3 fixes); simulate harness
- [ ] Per-well concentration audit from the simulator's command log
- [ ] Plate reader / PyLabRobot path and a human approval gate (live run only)

**Benchmark and grading**
- [ ] Push the candidate (paper, compound, target) list (`benchmark-v0`)
- [ ] Ground truth from held-out papers into the schema; paper-text / methods retrieval (Europe PMC) for the judge
- [ ] `benchmark/rubric.yaml`: tree, branch weights, range metric
- [ ] Judge: model from a different family, blinding, prompts, ~10 human labels for calibration
- [ ] Aggregation into `RESULTS` with uncertainty (bootstrap CIs; n is small)

**Glue**
- [ ] Merge `kg-scaffolding` into main; Nebius key in `.env` on the shared machine; confirm the 4 models; cost
  estimate for the run grid
- [ ] Trace exporter to the demo format; decide the demo repo split
- [ ] Owners and a timeline for the rest
