# Demo memory — 2026-11-08

**Start with [the current Brev / Codex Remote handoff](REMOTE_HANDOFF.md).** It records
workspace/branch state, private service operation, credentials locations (not values),
verification, failed live rehearsals and the next decisions. It supersedes historical
migration notes where they disagree about branch, authorization or credentials.

Active development: `demo/public-readiness`, deployed privately on Brev at runtime
commit `2717540` plus subsequent documentation updates. The permanent companion
clone is `/home/ruh/what_we_test_next_demo`; Brev uses
`/home/ubuntu/what_we_test_next`. Recheck Git status before editing either clone.

The consolidation branch is already merged into GitHub main (`f329771`). Subsequent
reference/public-readiness changes are on the development branch. Other contributors'
original workspaces were preserved; do not collect their unfinished work implicitly.

Nebius and Paperclip are authenticated on Brev. 29 tests pass. Four direct synthetic
simulations passed, but both fresh autonomous runs failed before compilation. No
public ports were opened. Private systemd services are enabled and healthy; a public
results viewer and HTTPS/auth configuration are prepared but not deployed.

- [Setup and operation](../SETUP.md): isolated installs, credentials, live/replay,
  tests, platform limits and failures.
- [Migration verification](../docs/11-08-2026.md): measured checks and remaining gaps.
- [Pipeline](../harness/PIPELINE.md): contract boundary, validation and compilation.
- [Scope](../docs/PROJECT_SCOPE.md): supplied inputs → planning → OT-2; screening separate.
- [Remaining TODOs](../docs/PIPELINE_TODO.md): outcome checklist and current progress.
- [Consolidation plan](../docs/DEMO_CONSOLIDATION.md): original acceptance criteria.
- [Historical agent handoff](agent_stage_handoff.md): original autonomous 2×2 rehearsal.
- [Historical pipeline record](pipeline_execution.md) and [real-data plan](real_pipeline_plan.md).
- [Packaged replay](../replays/README.md): synthetic inputs, real historical retrieval
  and simulations, no claim of physical execution or independent proof of autonomy.


The synthetic 2×2 case remains a software fixture. A reviewed real compound/strain
question, reference-protocol validation, reliable autonomous completion and public
access decisions remain pending. The local 5090 endpoint has not been identified.
