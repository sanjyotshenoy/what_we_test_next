# benchmark/: the questions, the answers, and the grading

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

- **Questions** the KB cannot answer, built by **holding facts out**: take known (compound, target) IC50 results
  (e.g. from ChEMBL), remove them from the biology KG, and ask about them. Start with about 5 hand-picked ones in
  one area, then grow.
- **Ground truth:** the assay that was actually run (from the held-out ChEMBL assay record), as a `GroundTruth`.
- **Writes:** `questions.jsonl` (`Question`), `ground_truth.jsonl` (`GroundTruth`), `held_out.csv` (the
  (compound, target) pairs `kg/biology/` must leave out).
<!-- TODO(final): pick the range-accuracy metric (it must penalize very wide ranges) before writing the grader. -->
- **Grading** (`python -m benchmark.grade agent/out/<run>.jsonl`, _to write_):
  - did it say the KB cannot answer, instead of quoting a memorized IC50?
  - field by field against the ground truth: assay type, readout, system, concentration range (does it bracket
    the true IC50?), dilution factor, number of points, controls, replicates
  - are the citations real node IDs in the graphs?
  - an LLM judge only for the free-text rationale
- **Aim 2** results come from `execution/` (does the protocol simulate, and do per-well concentrations match).

## Three-case pilot (2026-11-08)

A single-model, fixed-context run with usage accounting is recorded in
[`runs/gpt-oss-120b-pilot/RESULTS.md`](runs/gpt-oss-120b-pilot/RESULTS.md).
It includes complete final outputs, input snapshots, provider token receipts,
provisional Codex grades, and offline coverage diagnostics. It is not a validated
benchmark result. Run the non-billing checks with
`python -m benchmark.check_three_case_pilot`.

`python -m benchmark.run_three_case_pilot` is the paid runner; it refuses to repeat
an existing run. Its model/rates/settings are pinned to this historical pilot;
recheck live rates and set a new run directory before deliberately running again.
It uses `wwtn.llm.chat`, captures response usage without changing shared code, and
makes at most three requests with SDK retries disabled.
