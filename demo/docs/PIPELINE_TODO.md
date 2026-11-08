> Current operational state: [Brev / Codex Remote handoff](../memory/REMOTE_HANDOFF.md).
> Nebius and Paperclip are now configured on Brev; the blocker is failed autonomous
> model/tool execution, not missing credentials. Older migration wording below is historical.

> Migrated planning record. Current progress and verification: [memory](../memory/MEMORY.md).

# Real-data demo — adaptable TODOs

Updated 2026-11-08. Scope: big-picture points **2 (planning)** and **3 (execution)**.
The user expects schemas and team implementations to change. This is an outcome
checklist, not a commitment to today's field names, model, assay, or plate layout.
Current implementation/proof: [agent and stage handoff](../memory/agent_stage_handoff.md).

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

## Progress this migration

Installed and tested from a relocated source-only checkout; packaged explicit replay;
added tool budgets, complete-response tests, API boundary/stale/corrupt-artifact tests,
atomic writes and schema-version provenance. See [verification](11-08-2026.md).
Fresh autonomous live rehearsal awaits demo-local credentials. User confirmed keeping
the synthetic 2×2 case for now. Remaining items below are not claimed complete.

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
- [ ] **Harden agent orchestration.** Add focused tests for the complete-response
  transport, including malformed responses, cancellation, IDs and usage. Remove or
  clearly isolate the earlier unused streaming experiment. Verify dependency setup
  from a clean installation. Enforce tool/correction budgets in code; prompts alone
  did not prevent repeated failed submissions in an earlier run. Recheck compatibility
  when OpenCode/provider versions change. Never guess missing function names/arguments.
- [ ] **Finish stage reliability checks.** Add automated API tests for session isolation,
  stale protocol/report detection, artifact path boundaries, interrupted writes and
  absent/corrupt artifacts. Rehearse abort/new-session/model/key changes and reconnects.
  Fetch selected-run details rather than all simulator logs every poll as batches grow.
  Clarify legacy-page behavior under the new default planner before stage use.
- [ ] **Package a dependable fallback.** Preserve a reviewed, sanitized real trace with
  explicit fixture/live/saved provenance and input versions. The sanitized historical rehearsal is packaged under `demo/replays/`; new runtime
  artifacts remain ignored by Git. A saved manifest alone does not establish that an
  agent completed it autonomously. Rehearse service failures and an explicit replay
  path; test local Qwen only when requested. No silent fake data or automatic success.
- [ ] **Rehearse the final story and explain it together.** Run the chosen real case
  through the actual stage page, verify laptop access, and explain who does what:
  Paperclip/KG → planning agent → checks → compiler → simulator → UI. Keep the
  recorded physical proof of concept visibly separate. User-facing walkthrough is
  still pending; this session switched to documentation/handoff before that discussion.

## Parked until the scope calls for them

Screening/ranking integration (point 1), GNN work and its evaluation decisions,
physical robot execution, additional assay families, and publication/deployment.
Existing records cover those topics; this checklist does not authorize expanding scope.
