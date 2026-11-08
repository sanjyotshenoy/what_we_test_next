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

The follow-up [four-model pilot](runs/four-model-pilot/RESULTS.md) compares GLM 5.3,
DeepSeek V4.1 Flash 1017, Kimi K3.1 Pro and Nemotron 3 Super on identical packets.
It records 12 generation requests, token/cost ledgers, complete outputs, draft
grades and explicit abstentions. Offline checks:
`python -m benchmark.check_four_model_pilot`. The paid runner refuses to overwrite
an existing run and checks current model availability/prices against a $1 budget.

## Expanded 20-case run (2026-11-08)

[Results and limitations](runs/twenty-case-pilot/RESULTS.md) cover the same five models on all 20 cases: 85 successful new completions plus 15 reused outputs with matching input bytes/settings. Three additional Kimi attempts returned no usage receipt (two timeouts, one local interruption); explicit retries completed the matrix. `manifest.json` and `USAGE.md` distinguish confirmed token receipts from conservative allowances for unknown billing.

Run `python -m benchmark.summarize_twenty_case_pilot` for offline provenance, usage and diagnostic checks. These diagnostics are not new three-axis scientific grades. Existing pilot percentages still apply only to cases 1–3. The paid runner is `benchmark.run_twenty_case_pilot`; do not invoke `--execute` to inspect results.

## Astra-medium review of all 100 responses

[Three-axis scores and per-case evidence](judge/RESULTS.md) cover all five models × 20 cases, freshly scored by isolated, blinded Astra-medium agents under a [frozen prompt](judge/PROMPT.md). These are provisional AI judgments, not expert-validated scores. [Method and execution](judge/README.md) document calibration, blinding, validation and unavailable judge billing receipts. The historical three-case grades remain unchanged.

## Astra-medium candidate extension

[20-case Astra-medium run](runs/astra-medium-20/RESULTS.md) uses the same generation instruction and input bytes, with fresh generator and judge contexts. Astra also serves as the judge, and the collaboration interface differs from the earlier Nebius runs; same-model bias and unmatched serving/reasoning settings limit direct ranking. Raw outputs, execution provenance and unavailable token/billing receipts are documented with the results. Offline validation and aggregation: `python -m benchmark.astra_medium --summarize`.
