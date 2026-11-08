# Three-case pilot: GPT-OSS-120B

Executed 2026-11-08 UTC using Nebius `openai/gpt-oss-120b`. This is one sampled completion per case, **not a statistical benchmark result or a validated scientific assessment**.
<!-- TODO(final): domain expert must review these provisional grades, assay comparability, and the source-independence limitations in BENCHMARK.md. -->

## Main finding

The model selected the expected broad assay families and assembled the supplied step cards in prerequisite order. It did not consistently respect the requirement to use only supplied evidence: all three outputs added unsupported operating parameters, and case 1 claimed pilot verification that had not happened. Passing concentration-coverage arithmetic does not validate those procedures.

## Usage and cost ledger

| Case | Provider input tokens | Provider output tokens | Total | Estimated USD |
|---|---:|---:|---:|---:|
| 1 | 1,698 | 1,133 | 2,831 | 0.0009345 |
| 2 | 1,768 | 1,451 | 3,219 | 0.0011358 |
| 3 | 1,326 | 1,079 | 2,405 | 0.0008463 |
| **Total** | **4,792** | **3,663** | **8,455** | **0.0029166** |

Exactly three generation requests; no automatic retries, failed requests, repair requests, paid judge calls or model substitutions. Model-list and public pricing discovery requests preceded the run; no generation tokens were reported for those. The ledger covers this pilot's Nebius calls only, not teammates' usage or the Codex session.

Prices verified against https://tokenfactory.nebius.com/api/public/models_info before execution: $0.15 per million input tokens, $0.60 per million output tokens. Cached input counts were 64, 64 and 208 respectively. The estimate deliberately charges all input at the uncached rate; actual billed amount may be lower. Completion-token detail was null, so separate reasoning-token counts are unavailable; use the provider's aggregate completion count, not an invented breakdown. Invoice totals, taxes, currency conversion and remaining account balance were not available. This is about 0.00292% of a $100 budget; it does **not** establish that $99.997 remains in the shared account.

The preflight used the full 8,192-output-token cap for each call and a conservative UTF-8-byte input allowance plus framing margin. Its reservation is recorded in `manifest.json` and was below $0.10. This guard applies to this runner, not to other users of the key.

## Run conditions and isolation

- Same system instruction for every case, temperature 0, reasoning effort low, JSON-object mode, maximum 8,192 completion tokens; timeout 180 seconds; SDK retries disabled.
- Each request was independent, containing only the fixed instruction and that case's `.input.json`. No tools, conversation history, answers, reviewer files, graph explorer or web access were provided.
- The instruction allowed `null` when the original numeric output contract could not be supported, with an explanation. This was a pre-run, identical instruction for all three cases, intended to permit honest abstention. All three nevertheless returned numeric values.
- Original packets are copied here, and SHA-256 verified. `manifest.json` records the full prompt, settings, provider response IDs, returned model IDs, timestamps and raw usage objects. `.output.txt` preserves the returned final content, `.output.json` is its parsed representation. Internal reasoning text was not retained or used to grade.
- Calls go through `wwtn.llm.chat`. A response hook captures usage because the shared wrapper returns final text only; no shared code was changed and no key is saved in these artifacts.
- `diagnostics.json` is generated offline by `python -m benchmark.check_three_case_pilot`. Reference answers are read only by this post-run diagnostic, not by the paid runner.

## Provisional three-axis review

These grades were assigned by Codex after comparing the final outputs with the supplied packets and the predeclared draft rubric. They are **not independent human grades** and have not been calibrated. No average or overall pass rate is reported.

| Case | Suitability /2 | Steps /2 | Numerical soundness /2 | Evidence |
|---|---:|---:|---:|---|
| 1 | 2 | 1 | 1 | Correct biochemical assay family and broad order. Unsupported expression system, control identity, enzyme/substrate/ATP settings and reagent timings. Claims reaction conditions were “verified in pilot” despite no such evidence. |
| 2 | 1 | 1 | 1 | Correct broad biochemical family, but readout calls ADP-produced luminescence “inverse of kinase activity,” contradicting its own activity normalization. Ordered outline is coherent; ATP/Km assertions and kit timings/volumes lack supplied support. |
| 3 | 1 | 1 | 1 | Correct Rec-1 viability assay and explicit target-engagement limitations, but rationale overstates what a reference BTK inhibitor establishes about BTK-mediated growth inhibition. Many culture/reagent settings are supplied without evidence. Top concentration is at least explicitly labeled an assumption. |

A numerical score of 1 here means plausible arithmetic with incomplete evidence, **not confirmation that the laboratory settings are correct**. The reference CSVs do not establish full conditions, so scientific correctness of specific timings/volumes/Km values is not assessable. Case 1's fabricated verification is an evidence-integrity failure. Cases 2/3 have internal interpretation conflicts requiring review; neither receives full suitability credit. Honest unresolved slots would be preferable to unsupported claims of validation.

### Case-specific observations

**Case 1 — CHEMBL4278808 / haspin.** Proposed 100 µM top, 3-fold dilution, 10 points, triplicates. A named reference inhibitor and several kinetic/kit-specific values are absent from the packet. It calls other retained compounds “similar” even though the packet explicitly says retrieval is not similarity-ranked. It describes conversion as verified in a pilot; no experiment or pilot results were provided or run. Its limitations acknowledge assumed Km values, but do not undo the unsupported verification claim. The five citation IDs exist in the input; valid IDs alone do not substantiate these added settings.

**Case 2 — CHEMBL5426285 / haspin.** Proposed 10 µM top, 3-fold dilution, 8 points, triplicates. It correctly reproduces several retained example potencies, but the record does not justify ATP being at least ten times Km, particular reaction linearity or manufacturer reagent ratios. Citation entries contain explanatory text instead of bare IDs (four contract violations); extracted compound/assay IDs themselves are present in the input. The readout-direction inconsistency is visible in the final output and should be corrected before any experimental use.

**Case 3 — CHEMBL3936761 / Rec-1 viability.** Proposed 10 µM top, 3-fold dilution, 8 points, triplicates, despite no eligible retained measurement examples. It identifies the requested cellular endpoint and explicitly says viability cannot confirm target engagement. The top concentration is flagged as an assumption. Other details—medium, seeding density, exposure duration, reagent volumes and manufacturer timings—are stated as standard or supported without such evidence in the packet. The rationale's stronger mechanism wording conflicts with its caveats. No new biology or wet-lab validation was performed to resolve these claims.

## Offline checks and coverage

All three outputs are valid JSON, contain all requested top-level fields, use only known step cards, satisfy the supplied prerequisite order, and have mathematically valid positive series parameters. Case 2 fails the bare-ID citation formatting check. No extracted citation IDs are outside the input packets. Checks of source exclusions and input hashes pass.

| Case | Proposed series, nM | Reference nM | Points below / above | Brackets reference | At least 2 each side |
|---|---|---:|---|---|---|
| 1 | 100,000 → 5.0805; 10 points | 14 | 1 / 9 | Yes | No |
| 2 | 10,000 → 4.5725; 8 points | 1,225 | 6 / 2 | Yes | Yes |
| 3 | 10,000 → 4.5725; 8 points | 360 | 4 / 4 | Yes | Yes |

All three bracket the reference numerically. Case 1 lacks two points below the reference under the pilot diagnostic. These are **descriptive calculations only**: assay conditions are not established as comparable, and a broad range is not inherently a good experimental design. The two biochemical packets have the same retained measurements; this run does not establish that different ranges resulted from valid compound-specific evidence.

## Scope and next step

The three cases remain draft audit examples with unresolved cross-source independence and scientific validation (see `slides/talks/biohack/graph/BENCHMARK.md`). This run demonstrates execution, token accounting and visible failure modes, not validated general performance. No deterministic baseline was run; no claim is made that the LLM adds value over one. Have a domain reviewer audit the outputs and scores before scaling or changing the prompt. Avoid silently repairing these outputs and presenting the repairs as first-attempt results.
