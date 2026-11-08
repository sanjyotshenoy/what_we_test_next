> Historical source record (2026-11-07). Paths and status below describe the pre-migration implementation. Current instructions: [SETUP](../SETUP.md), [memory](MEMORY.md).

# Proposal validation and execution — 2026-11-07

**Later update:** See [agent/stage handoff](agent_stage_handoff.md) for the autonomous UI rehearsal and new team checkout, and [adaptable TODOs](../docs/PIPELINE_TODO.md) for next work. This record preserves the earlier state.

User requested the next core implementation steps after Paperclip wiring.
Team `main` refreshed, unchanged at `6a189cd`. No team files modified.

Implemented `harness/planning_pipeline.py`, `simulate_protocol.py`, two OpenCode
tools (`planning_submit`, `planning_simulate`), schema in planning_context and
updated planner prompt. Full usage/limits: `harness/PIPELINE.md`.

- Batch schema adds compound identity and field/evidence links around unchanged
  team `ExperimentProposal`. Current-session citation lookup verifies passage and
  context hashes; required field links enforced; optional background/system links
  allowed. Scientific entailment and declarations of user inputs are not verified.
- Supported designs compile per compound–species pair into separate sequential
  runs. No arbitrary single-species proposal limit. A 3 × 3 design produces 9 runs.
- Eight-channel physical fills are explicit: requested replicate rows and surplus
  technical wells recorded separately. No hidden change to requested sample size.
- Hard gates: supported assay/layout/units, exact supported controls, finite positive
  numbers, known oxygen tolerance, compatible atmosphere, team feasibility,
  concentration audit, checkable must-rules and compiler warnings except API ceiling.
  Uncheckable rules reported as needs_review. Source reference-antibiotic control
  is not implemented; requests for it are rejected rather than dropped.
- Artifacts include JSONL proposals, source snapshot, rule report, manifest, plate
  maps, source identities, protocols, off-robot run sheets, simulation reports/logs.
  Simulation is explicit not_run/pass/fail/timeout and pinned to protocol hash.

## Evidence

14 tests passed (8 pipeline + 6 retrieval). Includes malformed/unread citations,
session isolation, invalid units/numerics/layout/control/tolerance, rule failure,
source-label code injection, audit hard gate, timeout stopping and protocol tampering.

Diagnosed previous 300s simulator timeout: faulthandler under restricted sandbox
showed asynchronous file adaptation waiting inside Opentrons/anyio. Same generated
file outside sandbox completed in <1s, 267 commands. No model/container startup.

- Synthetic test fixture session `fixture-3x3`, batch `12194639acfe4ad2`: 9/9
  simulations passed, 267 commands each. Fixture names are explicitly synthetic.
- Live gpt-oss-120b agent fetched real context + PMC8368853 lines 1–10, then submitted
  a complete 2 × 2 proposal with explicit software-test inputs. First validation
  over-rejected useful optional `background`/`system` links. Fixed that check and
  compiled the ORIGINAL model payload unchanged; batch `3d23632b440444a6`, session
  `ses_e46a0d529ffeag5DHl7ypEPtxc`: 4/4 passed via direct backend simulation.
- During model correction attempts OpenCode reported invalid tool calls and then
  `Expected 'id' to be a string.` A single continuation of that session failed with
  the same ID error. No retry loop; simulated the already-compiled payload directly.
  The unattended full agent loop is NOT yet rehearsed/stable. Do not conceal this
  by reporting the backend success as a complete autonomous run.
- Trace files in ignored `harness/planning_runs/`: pipeline-agent-smoke.jsonl,
  model-original-submit.json, model-original-result.json, pipeline-agent-simulation.jsonl.
  The 13 simulator checks preceded the final rule-report addition; the final code's
  rule checks were verified in the offline tests, without rerunning identical transfers.

Next: stabilize multi-call orchestration (or implement a clearly labeled bounded
direct-provider fallback), then connect artifacts to the stage UI. No pushes,
physical robot actions, or persistent servers started in this task.
