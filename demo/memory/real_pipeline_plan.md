> Historical source record (2026-11-07). Paths and status below describe the pre-migration implementation. Current instructions: [SETUP](../SETUP.md), [memory](MEMORY.md).

# Real-data demo: points 2 and 3

**Later update:** See [agent/stage handoff](agent_stage_handoff.md) for the autonomous UI rehearsal and new team checkout, and [adaptable TODOs](../docs/PIPELINE_TODO.md) for next work. This record preserves the earlier state.

Triage: 2026-11-07 (client date). Team `main` fetched and confirmed at `6a189cd`.
Scope from `project_big_picture.md` and the user: supplied compounds -> grounded,
checkable experimental proposal -> OT-2 instructions. Screening/ranking (point 1)
remains independent. This is an implementation proposal, not a completed pipeline.

User clarification: the recorded single-species OT-2 run is a proof of concept,
not a limit on agent designs. The target includes multi-species/multi-compound
experiments (e.g. 3 bacteria × 3 compounds), simulated independently from that
recording. Paperclip literature access is now the first integration step; see
`paperclip_setup.md` for the installed and authenticated client.

## What exists and what it actually supports

| Component | Evidence in the current checkout | Integration consequence |
|---|---|---|
| Biology KG | 15,311 nodes; 19 kinase targets; 12,822 compounds; 17,538 INHIBITS edges, sourced to ChEMBL 37; 22 structure-only compound nodes | Real fetched data, but a kinase subset, not MIC panel evidence. None of the four MIC example species appears in the graph. |
| Protocol KG | 141 nodes / 367 edges; 8 protocol nodes; 3 curated template JSONs; PubChem/AGM provenance | Reuse routing, source observations, steps and rules. Agent-curated templates still need human review; real sources do not imply validated defaults for every species. |
| Proposal agent | `agent/propose.py`, `tools.py`, `kg_backend.py`, `anchor.py` | Real bounded tool-calling loop and trace callbacks. Prompt, tool output schema, analog lookup and anchor are kinase/IC50 oriented. Proposal tool omits panel, canonical units and growth fields. |
| Shared contracts | `wwtn/schema.py` | Already supports panel, concentration units, growth conditions, layouts, proposals and execution results. No schema edit needed for the first integration. |
| Execution | `execution/{lab,feasibility,plate,protocol,generate}.py` | Deterministic MIC plate and OT-2 generator, independent concentration audit, simulator adapter and off-robot run sheet. Reuse behind explicit validation. |
| Existing stage | `harness/stage/`, `.opencode/tools/` | Real OpenCode loop, but tools use the harness seed graph, simplified plate model and fixed MIC replay. Replace their data sources and events before claiming real integration. |
| Screening | `screening/` | Separate upstream work. No dependency for supplied-compound experiments. |

## Gaps that must not be hidden by a successful simulation

1. Kinase proposals must not enter the MIC compiler. Route by supported assay/template;
   unsupported assays stop with a clear result.
2. Multi-species rows currently share a single `inoculum` reservoir channel in
   `execution/protocol.py`. Labels on the map do not implement species-specific
   dispensing. Use the single-species run as a regression fixture; add a verified
   per-species liquid-source plan for newly proposed multi-species simulations.
   Do not constrain the agent to single-species designs.
3. The transfer sequence implements 2-fold dilution; other factors can disagree
   with the plate map. Refuse unsupported factors and make audit errors blocking
   in the harness (upstream currently emits warnings).
4. `execution.generate` initializes `simulated_ok=True` even if simulation was
   not requested. The harness must track not-run/pass/fail explicitly and only
   show pass after a completed simulation, preserving raw output.
5. The MIC example lists a reference-antibiotic control, but the map only allocates
   growth and sterility columns. Verify every requested control has a physical
   implementation or an explicit off-robot step; do not silently drop it.
6. Unknown oxygen tolerance, assumed lab capabilities, template applicability and
   provenance require explicit treatment. No kinase IC50 evidence may masquerade
   as MIC evidence; no mass/molar conversion without molecular weight.
7. The current trace/plate display assumes µM and replicate-only rows. Use the
   actual compiled map with units, species and prepared/final concentrations.
8. GraphBackend silently falls back to sample graphs if real files are missing.
   Real-data mode must fail instead, and record input hashes and the team commit.

## Proposed architecture

Keep integration in `harness/`, without editing team-owned folders or `wwtn/`.
Keep OpenCode as the stage agent engine; expose the team's real KG, protocol
retrieval and execution checks through narrow tools. Avoid running both the old
stage agent and the team proposer as competing orchestration loops.

One planning agent chooses a protocol and proposes parameters from supplied
compound/species inputs and retrieved evidence. It calls deterministic tools for
template conditions, rules, lab feasibility and plate audit. A rejected proposal
returns concrete violations for a bounded revision, not a silent patch. The
execution stage compiles the accepted structured proposal and runs the simulator;
it does not require a second LLM to rewrite Python.

Use `ExperimentProposal`/`ExecutionResult` JSONL at boundaries. Add a harness run
manifest and event log for metadata not represented by those shared models:
input hashes, source evidence, field derivations, model identity, validation
states, warnings, failures and replay status. Cite only evidence actually returned
to the agent. Show short decision summaries rather than raw model reasoning.

## Ordered milestones and acceptance criteria

### 0. Set up Paperclip evidence retrieval (client setup complete)

- Installed GXL Paperclip 0.8.16 in its own venv; browser authentication and
  search/metadata/passage retrieval passed. See `paperclip_setup.md`.
- Next expose bounded literature retrieval to the agent with source identities,
  dates and passages. Keep unrestricted demo research separate from benchmark
  cutoff/held-out filtering. No measurement is invented when retrieval has no answer.

### 1. Establish the offline execution baseline

- Inventory/hash real graphs, templates and lab configuration; reject sample fallback.
- Exercise the team's hand-written MIC example explicitly as an integration fixture,
  never label it an agent output or a new measurement.
- Add a harness validation adapter for supported assay, 2-fold transfers, positive
  numeric values, control coverage, species/source coverage, plate audit and explicit
  simulation status. Preserve the underlying team code.
- Keep the existing one-compound/one-species run as a regression fixture.
  Target supplied compound × species designs, including 3 × 3; compile into
  explicit runs/plates with distinct compound and inoculum identities.
- Acceptance: offline generation plus simulator log; invalid inputs demonstrably
  stop before being presented as ready. Multi-species designs can be proposed now;
  generated simulations must implement their inoculum mapping faithfully.

### 2. Build the real experimental-design agent

- Expose protocol retrieval, provenance, conditions, applicable rules, lab capabilities
  and proposal submission as OpenCode tools backed by team code/data.
- Supply compounds and intended assay/species as input; do not depend on screening.
- Extend the harness proposal tool to the current shared schema: units, panel,
  conditions and selected template. Keep selected template/evidence in the manifest.
- Separate observed source values, derived values, template defaults and user inputs.
  Missing compound-specific MIC evidence remains missing; defaults are not measurements.
- Validate citations and template/assay compatibility, then run deterministic checks.
  Bound tool rounds and revisions; record failures for inspection, without blind retries.
- Acceptance: one actual cheap-model run creates a schema-valid, cited MIC proposal
  from retrieved source-backed templates and supplied inputs. No hard-coded final answer.

### 3. Join proposal to compilation and simulation

- Save proposal JSONL, compile through the execution adapter, retain plate map,
  protocol, run sheet, validation report and raw simulator log under one run ID.
- Check requested controls and species against actual operations, not just strings
  in the proposal. Support multi-species only once distinct sources/destinations
  are represented and verified, or expose inoculation explicitly as a manual step.
- Acceptance: one run traces every displayed artifact to the same accepted proposal;
  simulation pass means software execution only, not biological validation or robot execution.

### 4. Connect the stage UI to those run artifacts

- Replace seed KG calls with the small real evidence subgraph retrieved during the run.
- Stream proposal, evidence, checks, compiled plate and simulation events.
- Show pending/failed/not-run states and lab assumptions explicitly.
- Use new simulator output for robot events. Old video can appear only as a labeled
  reference recording; never imply that it executes a newly proposed experiment.
- Acceptance: changing an input changes the compiled artifacts and corresponding UI;
  no stale plate/feed from another run.

### 5. Rehearse and preserve a real fallback

- Test missing graph, unsupported assay, bad units, failed audit, missing control,
  model error and simulator error.
- Save a completed actual agent trace and artifacts for explicitly labeled replay.
- Rehearse local-model fallback separately when requested; do not start Qwen now.
- Only then broaden compound batches, multi-species panels or protocol families.

## Verification during triage

- Team fetch succeeded; checkout was clean and already current at `6a189cd`.
- Graph counts above were measured directly from the CSVs, not copied from older docs.
- Attempted `WWTN_OFFLINE=1 ../.venv/bin/python -m pytest -q agent execution kg`:
  blocked by missing `pytest` in the workspace venv. No test-pass claim.
- Invoked the hand-written example with the existing OT-2 simulator on PATH, outputs
  in `/tmp/ouroboros-triage-mic`: protocol/run sheet generated, simulator timed out
  after its 300-second limit. No simulation-pass claim; investigate before retrying.
- No LLM calls, model/server startup, team code edits or pushes during this triage.

Paperclip evidence tools and structured submission/simulation are now exposed to
the separate OpenCode `planner` agent. Proposal validation and pair-specific
compilation are implemented; nine synthetic fixture runs and four runs from a live
model-generated software-test proposal passed simulation. The full agent loop
still encounters a tool-call ID error. Next: stabilize orchestration and connect
these artifacts to the stage UI. See `pipeline_execution.md` and
`harness/PIPELINE.md`; physical recording remains labeled as its own run.
