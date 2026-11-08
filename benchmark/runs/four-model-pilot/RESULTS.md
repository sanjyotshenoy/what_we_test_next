# Four-model pilot: same three experiment-design cases

Executed 2026-11-08 UTC. One completion per case/model; 12 successful generation calls. This is a small, fixed-context diagnostic pilot, not a calibrated leaderboard or proof of scientific validity.
<!-- TODO(final): human domain review and grading calibration are required before treating these scores as validated. Source-independence caveats in the case design remain open. -->

## Model selection and comparison

Requested GLM 5.3, DeepSeek “V5.1 Flash 1017”, Kimi K3.1 Pro and Nemotron Super. Nebius had no V5.1 match; the run used **DeepSeek V4.1 Flash 1017**, matching the earlier conversation, and explicitly announced this before running. Nemotron is **Nemotron 3 Super 120B A12B**, not the VL/Ultra variants. Exact API IDs are in the manifest.

All models received byte-identical case packets from the prior GPT-OSS run, the same system instruction and requested API settings: temperature 0, JSON-object mode, reasoning_effort low, max_tokens 8192. Requests were isolated; no tools, reviewer answers, raw graph or preceding outputs were included. SDK automatic retries were disabled. All responses finished with `stop` and parsed as JSON; there were no repair calls, paid judge calls or truncations.

The same nominal reasoning setting does not imply equal compute across architectures. Provider-reported output tokens include reasoning, where broken out; do not add those reasoning counts again. Model versions, prompts, usage objects and response IDs are retained in `manifest.json`; final content is saved in each model directory. Internal reasoning text was not retained or used for grading.

## Provisional scores

These are Codex reviews, not independent expert grades. The draft 0–2 rubric is unchanged: suitability, procedural soundness and numerical soundness. Equal-weight totals are illustrative, not pass rates. Detailed evidence follows and is machine-readable in `provisional_grades.json`.

| Model | Case 1 (suitability/steps/numbers) | Case 2 | Case 3 | Total /18 | Illustrative % |
|---|---|---|---|---:|---:|
| glm-5.3 | 2/1/1 | 2/1/1 | 2/1/1 | 12 | 67% |
| deepseek-v4.1-flash-1017 | 2/1/1 | 2/1/0 | 2/1/1 | 11 | 61% |
| kimi-k3.1-pro | 2/1/2 | 2/1/2 | 2/1/1 | 14 | 78% |
| nemotron-3-super | 2/1/0 | 2/1/1 | 2/0/1 | 10 | 56% |
| GPT-OSS-120B (earlier run) | 2/1/1 | 1/1/1 | 1/1/1 | 10 | 56% |

**Interpretation:** Kimi gave the best-grounded answers in this small review, especially on explicitly unresolved settings. It abstained from numerical series design in case 3; that is recorded as honest partial completion (1), not fabricated success or an invalid-value failure (0). Nemotron also abstained on that series, but invented other settings and omitted analysis. A partial score for abstention does not establish numerical adequacy. All three-case totals retain the same denominator and separately report whether coverage is assessable.

Numerical 2 for Kimi cases 1/2 reflects an internally consistent, contextually justified **provisional concentration series**, with unsupported lab settings explicitly unresolved. It is not a claim that all laboratory parameters were determined or validated. Procedural scores remain 1 for incomplete operating conditions. All unverified timings/volumes/Km values remain scientifically unassessed; explicit arithmetic/evidence contradictions can still be scored as errors. Do not interpret a one-point difference as robust superiority with only three cases and a single unblinded grader.

## Cost and token accounting

Live prices were fetched from https://tokenfactory.nebius.com/api/public/models_info before paid calls. The conservative reservation was **$0.526404**, below the local **$1 ceiling**. The estimate used input UTF-8-byte allowances plus framing margin and full output caps. No retries were allowed. This local guard does not limit teammates' use of the key.

| Model | Input tokens | Output tokens | Reasoning tokens (subset of output) | Estimated USD |
|---|---:|---:|---:|---:|
| glm-5.3 | 4,674 | 5,023 | 182 | 0.0286448 |
| deepseek-v4.1-flash-1017 | 4,709 | 11,915 | 9,118 | 0.0157107 |
| kimi-k3.1-pro | 5,041 | 4,977 | 1,650 | 0.0598520 |
| nemotron-3-super | 4,915 | 2,446 | 421 | 0.0036759 |
| **New batch total** | **19,339** | **24,361** | **11,371** | **0.1078834** |

New batch: **43,700 tokens, estimated $0.1078834**. Including the earlier GPT-OSS run: **52,155 tokens, estimated $0.1108** across 15 generation requests. This is about 0.111% of the stated $100 credits, not a reading of remaining balance.

Rates per million input/output tokens: GLM $1.40/$4.40; DeepSeek $0.30/$1.20; Kimi $2/$10; Nemotron $0.30/$0.90. Cached discounts are deliberately ignored for a conservative estimate. Provider invoice totals, taxes, currency conversion and account balance remain unavailable. Discovery calls were model-list/public-catalog reads, not generation requests. This ledger excludes teammates and the Codex session.

### Per-request ledger

| Model | Case | Input | Output | Total tokens | Estimated USD |
|---|---|---:|---:|---:|---:|
| glm-5.3 | case-1 | 1667 | 1728 | 3395 | 0.0099370 |
| glm-5.3 | case-2 | 1735 | 1891 | 3626 | 0.0107494 |
| glm-5.3 | case-3 | 1272 | 1404 | 2676 | 0.0079584 |
| deepseek-v4.1-flash-1017 | case-1 | 1672 | 4298 | 5970 | 0.0056592 |
| deepseek-v4.1-flash-1017 | case-2 | 1737 | 4173 | 5910 | 0.0055287 |
| deepseek-v4.1-flash-1017 | case-3 | 1300 | 3444 | 4744 | 0.0045228 |
| kimi-k3.1-pro | case-1 | 1780 | 1615 | 3395 | 0.0197100 |
| kimi-k3.1-pro | case-2 | 1851 | 1853 | 3704 | 0.0222320 |
| kimi-k3.1-pro | case-3 | 1410 | 1509 | 2919 | 0.0179100 |
| nemotron-3-super | case-1 | 1767 | 1019 | 2786 | 0.0014472 |
| nemotron-3-super | case-2 | 1836 | 846 | 2682 | 0.0013122 |
| nemotron-3-super | case-3 | 1312 | 581 | 1893 | 0.0009165 |

## Evidence for every grade

### glm-5.3

- **Case 1: 2/1/1.** Appropriate biochemical route and explicit unresolved settings. Series fields imply 1.524 nM minimum, but rationale says about 5 nM. Temperature is assigned 25 C and elsewhere called unresolved; unsupported <10% conversion rule is introduced.
- **Case 2: 2/1/1.** Correct family and contextual series rationale. Detection wording says equal volumes but gives 5 + 5 + 10 uL; vendor-typical numbers are assumptions, not input evidence. Some reaction criteria are introduced as requirements without packet support.
- **Case 3: 2/1/1.** Correct cellular endpoint and explicit limits on causality. Many settings are unresolved or assumptions. Rationale introduces compound mechanism/off-target facts absent from the packet; a compound name present in entity metadata does not support these claims.

### deepseek-v4.1-flash-1017

- **Case 1: 2/1/1.** Correct family, sensible card order, honest unresolved lab conditions. Arbitrary 100 uM/3-fold/8-point range lacks grounding in retained values and does not bracket the 14 nM reference; that diagnostic alone is not the scientific score.
- **Case 2: 2/1/0.** Procedure explicitly asks for 11 points, but both parameter string and top-level n_points say 10. Conflicting instructions prevent an unambiguous numerical design. Other lab settings appropriately remain unresolved.
- **Case 3: 2/1/1.** Correct viability endpoint and causality limitations; unresolved laboratory settings are acknowledged. 10 uM, 3-fold, 8 points and exposure conditions are clearly provisional, with no retained measurement evidence.

### kimi-k3.1-pro

- **Case 1: 2/1/2.** Correct family and order; missing conditions are unresolved rather than invented. Contextual 34–770 nM examples motivate a provisional 10 uM/3-fold/10-point range, and the stated 0.51 nM endpoint is arithmetically correct. Numerical credit concerns the supported series design and uncertainty handling, not validation of unresolved lab conditions.
- **Case 2: 2/1/2.** Correct family and order; correctly calculated range, explicit assumptions, same-target contextual evidence and unknown-origin comparability caveat. Numerical credit concerns coherent provisional series choices, not a validated full SOP.
- **Case 3: 2/1/1.** Correct cellular endpoint and explicit inability to infer BTK mechanism. All four numeric series/replicate fields are null with a clear lack-of-evidence explanation. This is honest partial completion, not an invalid numeric proposal; no concentration coverage can be calculated.

### nemotron-3-super

- **Case 1: 2/1/0.** Correct family and broad order, but says the highest contextual IC50 is 255 nM although input maximum is 770 nM. Says 8 points span to 15 nM although 10 uM/3^7 is 4.572 nM. Unsupported similarity, Km, optimal temperature and reagent claims; numerical score reflects identifiable evidence/arithmetic errors.
- **Case 2: 2/1/1.** Correct family and broad order; valid series fields. Unsupported ATP Km, reaction conditions and reagent timings, and unsupported claim that examples are similar compounds. A valid citation ID does not support these added values.
- **Case 3: 2/0/1.** Correct cellular endpoint and caveats; numeric series/replicates are honestly unresolved, but other culture/detection numbers are asserted without evidence. The procedure omits the analyse card and does not supply normalization, fitting or uncertainty-reporting instructions. Missing essential analysis earns zero on steps; no series coverage is calculable.

## Coverage and contract checks

Run `python -m benchmark.check_four_model_pilot` offline. Input hashes and byte equality with the earlier pilot pass; excluded source IDs are absent from model inputs. All 12 final outputs are valid JSON with required top-level fields, use known step-card IDs and satisfy the prerequisites of the cards they include. Prerequisite checks alone do not catch an omitted final analysis stage: Nemotron case 3 demonstrates this limitation. All citation strings are recognized IDs from the packet (step-card IDs count as valid); that does not validate claims attached to those citations.

| Model | Case 1: brackets / ≥2 each side | Case 2 | Case 3 |
|---|---|---|---|
| GLM 5.3 | Yes / Yes | Yes / Yes | Yes / Yes |
| DeepSeek V4.1 Flash 1017 | No / No | Yes / Yes* | Yes / Yes |
| Kimi K3.1 Pro | Yes / Yes | Yes / Yes | N/A — series null |
| Nemotron 3 Super | Yes / Yes | Yes / Yes | N/A — series null |

*DeepSeek case 2 diagnostics use the structured `n_points=10`; its prose says 11, so the output itself is internally inconsistent. No silent repair was made. GLM case 1's structured series ends at 1.524 nM although its prose says about 5 nM. Nemotron case 1 ends at 4.572 nM although its prose says about 15 nM. Automated checks use structured fields and manual review identifies these disagreements.

All coverage calculations are descriptive, **conditional on assay comparability**, which is not established by these records. A broad range that happens to contain the reference does not prove a good experiment. The two biochemical inputs share the same retained contextual measurements. Cases are correlated and deliberately selected; there is no random holdout sample or uncertainty estimate here.

## Reproduction and limitations

`benchmark/run_four_model_pilot.py` routes all paid inference through `wwtn.llm.chat`, captures usage without editing shared code, rechecks model availability and rates, enforces a conservative $1 reservation and refuses to overwrite an existing manifest. Do not remove that guard to rerun casually. The run artifacts contain no credentials.

No deterministic baseline, repeated seeds, expert validation or paid grading run was added. Review the actual outputs before using these scores in slides; full source-independence/assay-comparability concerns remain in the case design. Better evidence discipline is promising, but these results do not establish that LLM assembly improves on a deterministic template pipeline.
