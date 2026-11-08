# Cited proposals to simulated OT-2 runs

`planner` has six bounded domain tools:

1. `planning_context`: real MIC template, lab facts, submission JSON Schema.
2. `biology_lookup`: exact compound/species resolution and raw MIC observations from the bacterial graph.
3. `literature_search` / `literature_read`: discover sources and read citable passages.
4. `planning_submit`: validate the batch, save shared-schema JSONL, compile pair-specific protocols.
5. `planning_simulate`: run the isolated OT-2 simulator, stopping on the first failure.

```bash
demo/harness/opencode_server.sh run --agent planner --model nebius/openai/gpt-oss-120b 'YOUR QUESTION AND SUPPLIED COMPOUNDS/SPECIES'
```

The Nebius provider uses a complete-response transport to avoid malformed streamed
tool metadata. OpenCode owns the loop; no hidden model retry occurs. Session attempt
budgets are enforced in code. See [SETUP](../SETUP.md) and the
[historical autonomous rehearsal](../memory/agent_stage_handoff.md).

## What validation means

The batch envelope carries one compound identity per `ExperimentProposal`, plus
field-level evidence links (`field`, `kind`, `citations`, `explanation`). The
proposal's experiment uses the team schema unchanged. `planning_context` returns
the full submission schema; `python -m demo.harness.planning_pipeline schema` also emits it.

Checks include:

- Unique compounds/question IDs; explicit canonical concentration units and positive values.
- Citation IDs were actually retrieved in this OpenCode session; paper passage hash
  and current template/lab hashes agree. Search summaries are not citable passages.
- Links cover every required field. Observed claims cite a read paper or a retrieved KG measurement;
  other non-input claims cite retrieved evidence. Optional background/system/rationale
  links are allowed. Unresolved open questions prevent compilation.
- MIC assay, supported layout, 2-fold series, growth/sterility controls, known oxygen
  tolerance and compatible requested incubation atmosphere.
- The protocol KG's machine-checkable `must` rules; uncheckable rules remain
  `needs_review` in `rules.json`, never automatically pass.
- Team feasibility checks, independent concentration audit, implemented steps and
  compiler resource checks. Audit disagreements block output.

This checks provenance and structure, not whether each scientific claim follows
from its citation. User-input declarations and biological applicability still need
review. The source template's reference-antibiotic control is explicitly **not**
implemented. A proposal requesting it is rejected, not silently simplified.

## Multi-compound and multi-species execution

Every compound–species pair becomes a **separate sequential OT-2 run**, reusing
the team's tested MIC compiler. A 3 × 3 batch generates nine protocols. Each has
explicit medium, compound and inoculum identities for reservoir A1/A2/A3.
Reload labeled sources and consumables between physical runs; this is not an
automatically packed mixed-species plate.

The confirmed pipette fills eight rows at a time. The original proposal's requested
replicate count is preserved; the execution map records requested rows and surplus
technical wells separately. Surplus wells are not silently counted as requested
independent replicates. Per-run feasibility does not guarantee aggregate consumable
availability: the manifest records total plates/tips/rack loads and listed inventory.

Artifacts live under ignored `demo/harness/planning_runs/<session>/batches/<batch_id>/`:

- `batch.json`, `proposals.jsonl`, `evidence.json`, `rules.json`, `manifest.json`.
- Per run: `protocol.py`, `plate.json`, `sources.json`, `run_sheet.md`.
- After simulation: `simulation.json` (full simulator command log), `simulator.log`.

Simulation state is explicitly `not_run`, `passed`, `failed` or `timeout`.
Changed protocol hashes cannot reuse a simulation result. No tool connects to a robot.
The recorded single-species OT-2 run is a separate proof of concept, not execution
of any newly proposed batch. Incubation and measurement remain off-robot steps.

## Verification and environment

See [installation and tests](../SETUP.md) and [current verification](../docs/11-08-2026.md).
The isolated simulator uses demo/.venv-ot2 and a finite 30-second worker.
The planner UI renders these artifacts; the original static page remains unchanged.
New manifests include artifact version 1 and the active shared-schema hash. Older
replay manifests remain interpretable and are labeled saved evidence.

The bacterial adapter deliberately bypasses the kinase-oriented KG potency helper.
It preserves raw relations, units and assay/document nodes, hashes the graph and
returned payload, and does not aggregate strain-level measurements into species
claims. Unknown identities and absent pairs stay distinct. Benchmark filtering and
scientific entailment remain human-review work, not implied by a valid citation.
