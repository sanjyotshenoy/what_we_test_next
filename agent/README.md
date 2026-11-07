# agent/: aim 1, propose the missing experiment

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

Given a `Question` the knowledge base cannot answer ("does compound X inhibit target Y?"), decide whether the KB
already answers it, and if not, propose the experiment that would: an `ExperimentProposal` grounded in both graphs,
citing the nodes it used.

- **Reads:** `benchmark/questions.jsonl` (`Question`), `kg/*/graph/{nodes,edges}.csv`. Never `ground_truth.jsonl`.
- **Writes:** `out/<run>.jsonl`, one `ExperimentProposal` per question (`wwtn/schema.py`).
- **Flow:** resolve compound and target in the biology KG → get the target class → retrieve a protocol template by
  target class and assay format → the LLM fills the parameters (concentration range from similar compounds'
  potencies) and cites node IDs.
- **Baselines** (same model, for a fair comparison): bare LLM · LLM + literature search · LLM + both graphs.
- **Run:** `python -m agent.propose --questions benchmark/questions.jsonl --out agent/out/kg.jsonl`, or one
  question: `python -m agent.propose --question "Does imatinib inhibit the KIT kinase, and how potently?"`.
  `--runs-js slides/talks/biohack/demo/runs` also writes the trace for the demo page; `--model` picks the LLM.
- **Live demo:** `python -m agent.server` serves the deck and the demo page with the agent behind it (see
  `slides/talks/biohack/demo/README.md`).
- **How it works:** `tools.py` puts the two graphs behind three functions the model can call (`bio_kg_resolve`,
  `bio_kg_analogs`, `protocol_kg_templates`); `propose.py` is a tool-calling loop on `wwtn.llm.chat_raw` that
  ends when the model calls `propose_experiment`; `trace.py` records every call, the model's reasoning between
  calls and the proposal, which is what the demo page plays. Until `kg/*/graph/` exist, the tools fall back to
  the hand-written sample in `data/sample_kg/` (TODO(final) there).
- LLM calls go through `wwtn.llm` (`chat_raw` for tool calling); the model ID is recorded in each proposal.
- Baselines (bare LLM, LLM + literature search) are not written yet. <!-- TODO(final): baselines -->
