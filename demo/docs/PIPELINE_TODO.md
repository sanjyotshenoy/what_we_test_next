# Real-data demo — adaptable TODOs

Updated 2026-11-08. Scope: big-picture points **2 (planning)** and **3 (execution)**.
The user expects schemas and team implementations to change. This is an outcome
checklist, not a commitment to today's field names, model, assay, or plate layout.
Current implementation/proof: [memory](../memory/MEMORY.md),
[judge runbook](JUDGE_RUNBOOK.md), and [verification log](11-08-2026.md).
The earlier agent handoff is historical.

## Preserve these principles as the implementation changes

- Supplied compounds/species enter planning; screening remains a separate upstream workstream.
- The agent retrieves evidence and proposes; explicit, inspectable checks decide whether
  compilation can proceed. Keep tools and data adapters separate from agent prompting.
- Preserve source identity, actual passages, provenance, units, missing information,
  and the difference between observations, defaults, derivations and user inputs.
- Multiple compounds/species are in scope. The historical single-species recording
  is a proof of concept, not a product restriction or proof of a new proposal's execution.
- Proposed, validated, compiled, simulated and physically executed are different states.
  A simulator pass must never imply a biological result or physical execution.
- Team contracts stay team-owned. Adapt at the harness boundary instead of freezing
  or silently modifying shared schemas to fit this demo.

## Verified progress

Installed and tested from a relocated source-only checkout; packaged explicit replay;
added tool budgets, complete-response tests, API boundary/stale/corrupt-artifact tests,
atomic writes and schema-version provenance. See [verification](11-08-2026.md).
Nebius and Paperclip are authenticated on Brev. Three consecutive autonomous runs
with the final GLM settings completed eight simulations; 34 tests pass. One run
exercised rejection and agent correction of duplicate question IDs. The private
judge viewer opens reviewed results, and the fixed 30-second robot recording plays
independently. User chose view-only judges while the team operates privately.
Brev now publishes the read-only judge/sequential viewer; the shared operator is
authenticated for the current org-member allowlist. Eight new four-model sessions
provide sixteen additional simulator passes (see PRECOMPUTED_EXAMPLES.md). Assay
parameters remain supplied synthetic inputs, including real-identity examples.

## Next useful work, in order

- [x] **First: consolidate into the team demo.** On a separate team-repo branch,
  reconcile the working Ouroboros runtime, required dependencies/install instructions,
  documentation and memory into `what_we_test_next/demo/`, preserving other workstreams
  and existing demo/slide entry points. Follow [the consolidation plan](DEMO_CONSOLIDATION.md)
  before the feature work below. The user will continue night-duty work in that folder.

- [x] **Reconcile the latest team interfaces.** Sync and inspect schemas, protocol rules,
  graph access and execution APIs before another implementation step. Keep a small
  adapter/capability boundary; derive agent-facing schemas from the active contracts
  where practical. Track artifact/schema versions so old saved runs remain interpretable.
  Today's control labels, assay restrictions and per-pair scheduling belong to the
  current compiler capability profile, not universal scientific requirements.
- [ ] **Choose and review a real demonstration question.** Agree on actual compounds,
  species/strains, what is unknown, and the intended scientific claim. The successful
  2×2 rehearsal uses explicitly synthetic experimental inputs; do not rename it as
  a real-data scientific demonstration. Retain real evidence only for claims it supports.
- [x] **Connect the new bacterial KG to planning.** Team commit `5363a6f` added bacterial
  graph sources and a graph explorer. Check identity mapping, coverage, missingness
  and provenance before using it. The planner now has bounded `biology_lookup`, with exact IDs/names, raw MICs,
  censoring, units, provenance and graph/payload hashes. Scientific review remains open.
- [ ] **Strengthen evidence and applicability review.** Citation existence/hash checks
  do not prove that a passage supports a proposed value or that a template applies
  to a new strain/compound. Surface disagreement, unsupported assumptions and gaps.
  Keep held-out benchmark access/filtering separate from unrestricted demo retrieval.
- [ ] **Generalize execution only when supported.** Express capabilities and reject
  unsupported designs clearly. Have the team review required controls, source-liquid
  identity, replicate accounting, units, aggregate supplies and off-robot steps.
  Current separate sequential pair runs are one implementation, not a permanent
  multi-species design constraint. Expand layouts/controls only with corresponding
  compiler and audit support.
- [x] **Verify the bounded demo agent loop.** Typed submission schema, exact citation-ID
  feedback, malformed/truncated response rejection, finite tool/model-step budgets,
  cancellation transport checks and explicit model configuration are implemented.
  Three consecutive final-settings rehearsals passed. Keep earlier failures visible;
  this does not guarantee every future model response will succeed.
- [x] **Verify current UI and artifact boundaries.** Tests cover session isolation,
  stale/corrupt artifacts, download boundaries, busy-run guards, stop dispatch,
  desktop/mobile layout and video playback/seeking. The final live browser run kept
  video playing and restored controls after simulation. Private services and their
  prepared defaults were checked after restart.
- [ ] **Broaden reliability coverage as needed.** A clean installation of the newest
  dependency changes, full outage/reconnect and active-run recovery drills, physical
  reboot recovery, and larger-batch polling optimization are not established by the
  current checks. Recheck provider/tool compatibility when versions change.
- [x] **Prepare an explicit saved-results fallback.** The private judge viewer serves
  only reviewed successful sessions without depending on live inference/retrieval.
  Historical packaged replay remains in `demo/replays/`. New artifacts and media are
  ignored local files and must be transferred separately when moving hosts. Saved
  results are labelled saved; no automatic model or fabricated-result fallback.
- [ ] **Rehearse the presentation with the team.** The software and browser walkthrough
  is verified and documented in the runbook. Confirm the presenter's private laptop
  connection and narrative with the team. Keep real KG evidence, synthetic assay
  settings, simulated execution and the separate physical recording distinct.

## Parked until the scope calls for them

Screening/ranking integration (point 1), GNN work and its evaluation decisions,
physical robot execution and additional assay families. Public read-only viewing and
authenticated operator access are now configured; see the current handoff. This
checklist does not authorize expanding the audience or exposing new endpoints.

## Public access update — 2026-11-08

The user subsequently authorized public operator-layout viewing plus live runs
with a visitor-supplied Nebius key. `/sequential` remains intact. Public `/planner`
is a separate bounded worker path, without saved/inherited Nebius credentials or
private OpenCode access. Browser ownership, cancellation, key transport and 28
affected regression tests passed. See MEMORY.md and the dated verification log.
TODO(final): Rehearse this new public transport with a visitor-supplied key; no
paid end-to-end public run has been claimed. Existing private operator credentials
remain isolated and were not copied to the public path.
