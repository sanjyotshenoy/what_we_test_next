# Jimmy's OT-2 MIC benchmark snapshot

Imported from `step3_MIC_benchmark.zip`, supplied by Ramith on 2026-11-08.
Owner/source: Jimmy. The 78 source files are preserved byte-for-byte; macOS
resource-fork files (`__MACOSX`) were omitted.

## Results for slides

- [Before/after report](candidates_step3/benchmark_before_after.md)
- [Leaderboard CSV](candidates_step3/leaderboard.csv)
- Raw scores: [before](candidates_step3/results.json), [after](candidates_step3/results_after.json)
- [Repair history](candidates_step3/repairs.json) and [model notes](candidates_step3/notes.json)
- [Prompt](tasks/step3_prompt.txt), [rubric](rubrics/step3_rubric.csv), and
  [reference protocol](protocols/step3_standard_answer.py)

The snapshot contains one initial sample for each of five models, plus up to
three repair rounds. Model directories retain answers, reasoning, extracted
protocols, configuration, token usage, and cost metadata. Names and costs are
reported as supplied, not independently verified provider claims. These are
protocol-generation/simulation benchmark results, not measured biological MICs
or proof of a successful physical robot run.

<!-- TODO(final): Independently reproduce the supplied simulator scores and confirm
model identifiers and cost accounting before presenting them as verified results. -->

## Reproducing the report

From the repository root, with Python 3:

```sh
python3 -m benchmark.step3_MIC_benchmark.step3_report
```

This regenerates the Markdown report and CSV from the included JSON, without
making model calls. It overwrites those two report files.

The original scoring script requires Opentrons; the repair script documents
version 8.8.2. Historical absolute paths in the JSON refer to the original
machine. The source scripts and JSON are retained as archival evidence rather
than converted to the shared pipeline's JSONL contracts.

<!-- TODO(final): Before running generation or repair in this repo, adapt the
archived direct HTTP client to wwtn.llm.chat, fix step3_repair's sibling import
for module execution, and resolve historical paths. No generation or repair
calls were made during import. -->
