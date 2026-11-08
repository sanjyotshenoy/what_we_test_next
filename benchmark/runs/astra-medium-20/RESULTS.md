# Astra medium: 20-case benchmark extension

**Provisional AI judgments, not expert validation. Astra both generated and judged this extension in separate fresh contexts; same-model preference bias is possible.**

## Scores

All 20 responses scored 2 for suitability and 1 for procedural soundness. Numerical soundness was 2 in cases 1 and 12 and 1 in the other 18. The judge treated these as coherent but incomplete proposals, with unresolved operating conditions and frequent numerical abstention; zero flagged critical failures does not mean executable or validated protocols.

| Candidate | Suitability /2 | Procedure /2 | Numbers /2 | Mean total /6 | Cases with critical failure |
|---|---:|---:|---:|---:|---:|
| Astra medium | 2.00 | 1.00 | 1.10 | 4.10 | 0/20 |
| kimi-k3.1-pro | 2.00 | 1.00 | 1.40 | 4.40 | 0/20 |
| deepseek-v4.1-flash-1017 | 2.00 | 1.00 | 1.00 | 4.00 | 1/20 |
| glm-5.3 | 1.80 | 0.90 | 0.75 | 3.45 | 8/20 |
| nemotron-3-super | 1.90 | 0.45 | 0.50 | 2.85 | 17/20 |
| gpt-oss-120b | 1.45 | 0.85 | 0.05 | 2.35 | 19/20 |

## Exact design and comparison limits

- Same 20 input packet bytes and generation instruction as the existing five-model run. Input hashes, execution agent IDs and raw output hashes are in [manifest.json](manifest.json). One response per case; no output repair, retries or selection.
- Fresh `gpt-6-astra` generator at **medium** reasoning per case, with no inherited conversation, judge rubric, reviewer answers or other responses. File tools only transport the input and final output; browsing and retrieval are prohibited.
- Prior candidates ran through Nebius at low reasoning, temperature 0, JSON mode and an 8192-token cap. The collaboration interface cannot match/enforce those settings and adds its own system/tool scaffolding. This is a controlled-context extension, not an identical-serving-settings model comparison.
- A different fresh Astra-medium judge scores each response using the exact original frozen v1 rubric and incomplete endpoint guidance. Model names, prior scores and hidden potency are withheld; identity may still be inferred from style. Same-model bias is not eliminated by fresh contexts.
- The original four synthetic rubric-anchor checks remain applicable because the rubric is unchanged. They do not establish expert agreement. There is no repeated-judge variance estimate, independent judge-family review or wet-lab validation.
- All grade JSON passes literal-quote, evidence-path, schema and arithmetic checks. That does not establish scientific correctness. Unknown lab conditions and assay compatibility remain not assessable.
- Equal-weight totals are descriptive. Critical failures must not be averaged into a passing result. The 20 purposive cases are not a representative independent sample.

## Usage

20 generation tasks and 20 judge tasks through Codex collaboration. **No Nebius API calls. Provider token counts and billing are unavailable**, not zero. Output character and whitespace-word counts are stored as text size diagnostics, never as token receipts. The $100 Nebius credit balance was not queried or changed by this workflow.

## Per-case evidence

| Case | Suitability | Procedure | Numbers | Total /6 | Critical failures | Judge rationale |
|---|---:|---:|---:|---:|---:|---|
| case-1 | 2 | 1 | 2 | 5 | 0 | [evidence](../../judge_extension_v1/grades/af056fef56fd29cd.json) |
| case-2 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/85ea639f4b6f0a5b.json) |
| case-3 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/7b5443b7e3f4114e.json) |
| case-4 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/f2c2344036f8f2cb.json) |
| case-5 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/b8349222a59ba35e.json) |
| case-6 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/7e8a245aa0565508.json) |
| case-7 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/67866884469337a5.json) |
| case-8 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/66d8be9031aeb33e.json) |
| case-9 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/dedd0c8537a9ad79.json) |
| case-10 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/92f2de9bd49f1d56.json) |
| case-11 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/64a8c2a259e63e6d.json) |
| case-12 | 2 | 1 | 2 | 5 | 0 | [evidence](../../judge_extension_v1/grades/7b8352c6aee9fafe.json) |
| case-13 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/1dc30f7c931a2dc9.json) |
| case-14 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/58b36d3478a9e1e2.json) |
| case-15 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/12d17e0288763797.json) |
| case-16 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/6f42f71aefee60ae.json) |
| case-17 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/253175673be1fa96.json) |
| case-18 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/f1c31e8204e65933.json) |
| case-19 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/c6699c5ffe31f2dc.json) |
| case-20 | 2 | 1 | 1 | 4 | 0 | [evidence](../../judge_extension_v1/grades/9cb3ff8e878ff13d.json) |

## Reproduce offline

Run `python -m benchmark.astra_medium --summarize`. This validates and aggregates saved artifacts without inference. Generation and grading require fresh isolated collaboration agents as recorded in the manifests. Historical comparison: [original five-model review](../../judge/RESULTS.md).
