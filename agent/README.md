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
- **Run:** `python -m agent.propose --questions benchmark/questions.jsonl --out agent/out/kg.jsonl` _(to write)_
- LLM calls go through `wwtn.llm.chat`; record the model ID in each proposal.
