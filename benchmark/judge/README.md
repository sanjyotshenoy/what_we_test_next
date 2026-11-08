# Blinded Astra-medium judge pipeline

This grades the 100 saved final outputs from the twenty-case run. It does not regenerate experiment proposals or replace their usage ledger. Scores are provisional AI judgments, not expert scientific validation.

## Frozen evaluation design

- `PROMPT.md`: rubric v1, score anchors, evidence requirements and JSON contract. SHA-256 in `manifest.json`.
- `prepare.py`: deterministic anonymization/shuffle; writes one packet per response. Each packet contains the generator's exact input, incomplete reviewer endpoint guidance, and the final response text. It excludes model names, previous grades, usage/latency, hidden IC50s and coverage diagnostics.
- `private/mapping.json`: unblinding map, accessible only to the aggregation/review stage. Blinding is an execution restriction, not filesystem access control.
- `calibration/`: controlled error/abstention fixtures. These test rubric comprehension; they are not expert calibration of all scientific judgments. Expected scores are kept in `private/calibration_expected.json`, unavailable to graders.
- `grades/`: one unedited judge JSON per production response, written by a fresh isolated judge agent.
- `execution.json`: agent/task provenance and execution status. Requested judge is `gpt-6-astra`, reasoning effort `medium`; provider snapshot/version beyond the exposed model alias is unavailable.
- `validate.py`: exact evidence-quote matching, schema, file hashes, evidence paths and judge arithmetic. These checks cannot establish scientific correctness.

## Execution

1. Run `python -m benchmark.judge.prepare` before grading. Freeze the prompt and manifest. Never regenerate packets or edit the rubric in a completed run directory without versioning the run.
2. A coordinator reads only the manifest and packet filenames. For each calibration job, spawn a fresh `gpt-6-astra` subagent with `reasoning_effort="medium"` and `fork_turns="none"`. Give it only the absolute prompt, assigned packet and output paths. The judge may not browse, read other files, access model identities, or spawn agents.
3. Root validates calibration outputs against the concealed expectations. Start production only after those checks pass. If the rubric changes, change its version/hash and rerun calibration before scoring any production outputs.
4. Repeat the same single-response fresh-agent invocation for all 100 jobs, with at most three workers concurrently (the initial eight production jobs used two while a coordinator occupied the fourth slot). No judge sees another response, prior score, or calibration answer. The coordinator does not grade or unblind.
5. Run `python -m benchmark.judge.validate --complete`. Preserve original drafts if a formatting/evidence-path correction is necessary; keep an audit record. Never alter a substantive score merely to satisfy a validator or a preferred ranking.
6. Unblind only for aggregation. Report per-axis means, per-case scores, critical-failure counts, uncertainty and low-confidence cases. A sum/percentage is illustrative, not a pass rate. Do not average away critical failures or imply a statistically robust winner from this small purposive suite.

## Cost and limitations

Astra runs through Codex collaboration agents, not `wwtn.llm.chat`/Nebius. That interface exposes requested model and reasoning effort but not provider token/billing receipts. Record this as **unavailable**, not zero-cost. No additional Nebius requests are made by this pipeline. The original generation usage remains in `benchmark/runs/twenty-case-pilot/`.

Synthetic calibration does not establish expert agreement. The incomplete reference data cannot validate optimal incubation conditions, lab compatibility or biological efficacy. The judge can assess observable errors, grounding and uncertainty handling; missing ground truth remains explicitly not assessable. Model identities are withheld by instruction and task isolation; the shared filesystem is not a security boundary.
