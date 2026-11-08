> Migrated planning record. Current progress and verification: [memory](../memory/MEMORY.md).

# Next session first: consolidate Ouroboros into the team demo

Night-duty follow-up from the user: tonight's first task is to bring the working
Ouroboros demo into **`what_we_test_next/demo/`**, on a separate branch. The team
will be offline; continue work in the demo without disturbing other workstreams.
The intended home is one repository, `what_we_test_next`, including everything
needed to understand, install and run the demo. This supersedes the earlier
separate-repository implementation plan. **Implemented; see the current verification record. Fresh autonomous rehearsal awaits credentials.**

Start with this plan, then [the verified handoff](../memory/agent_stage_handoff.md).
The other [pipeline TODOs](PIPELINE_TODO.md) come after consolidation. Schemas and
team internals remain changeable; migration should preserve behavior, not freeze them.

## Scope and first steps

1. Inspect both repositories' working trees; preserve existing changes. Recheck
   running processes before touching launchers or ports. Read the team's `AGENTS.md`,
   `CONTRIBUTING.md`, `demo/README.md` and any new demo-local instructions. Refresh
   the clean team checkout from its latest main, then create a branch such as
   `codex/consolidate-demo`. Do not work on team main or push without a request.
2. Inventory the runtime, config, dependencies, assets, tests and local-only state.
   Compare the existing demo and live-agent integration before replacing anything.
   Keep work under `demo/`; use existing team schema/KG/execution modules as imports.
   Do not modify `wwtn/`, `agent/`, `execution/`, `kg/`, screening or slides merely
   to accommodate the migration. Record the decision in `DISCUSSIONS.md` as required
   by team instructions; that bookkeeping does not authorize broader shared-code edits.
3. Port a coherent runnable package, update installation and agent instructions,
   and prove it works without the Ouroboros checkout. Only then resume feature work.
   Keep the original working source available until reconciliation is verified;
   avoid maintaining two active implementations thereafter.

## What to reconcile

| Current source | Required result in the team demo |
| --- | --- |
| `harness/planning_evidence.py`, `planning_pipeline.py`, `simulate_protocol.py` | Evidence retrieval, validation, compilation and simulation using the team's active contracts and implementation |
| `harness/stage/` | Stage server, new planning UI, actual artifact reader, prompts, assets and relevant tests |
| `.opencode/tools/`, `.opencode/providers/`, `.opencode/package.json`, `harness/opencode/opencode.json` | Isolated demo agent configuration/tools/provider adapter, pinned JS dependencies and reliable discovery from the new location |
| `harness/opencode_server.sh`, `stage.sh`, `paperclip.sh`, install manifests | Demo-local install/start/stop/check commands with configurable paths/ports and clear ownership of processes |
| `harness/README.md`, `PIPELINE.md`, Paperclip setup and focused `project_memory/` records | Team-readable setup, architecture, evidence/limitations, general TODOs and a clear memory entry point inside `demo/` |
| Essential session notes and the project big picture | Relevant decisions and continuity, with links that resolve entirely inside the team repository; distinguish history from current instructions |
| Verified run artifacts and fallback material | A small reviewed, sanitized rehearsal/replay bundle where appropriate, explicitly labeled as synthetic inputs with real retrieval/simulation; preserve provenance |

The final subdirectory/package names are implementation choices after inspection.
Do not copy the entire workspace, unrelated GNN/serving projects, global settings,
or Spark administration history into the demo's required runtime. Keep optional
machine-specific reference material clearly separate from portable instructions.

## Existing team demo compatibility

At the inspected team commit `5363a6f`, `demo/` already contains a static page,
fonts, recorded traces and a live interface to `agent.server`. Preserve useful
existing work and explicit mock/real labels. `demo/index.html` is a slide entry
point, including `?theme=dark`; `slides/talks/biohack/demo` points to it through a
symlink. Inspect again next session: the team may have changed it.

Reconcile the UI/backend entry points deliberately; do not silently overwrite the
team demo or leave two competing default agent loops. Keep static/replay access
working where required by the deck, while documenting that the full live planner
needs its backend. Avoid touching slides or triggering a deployment for this task.

## Installation and runtime deliverables

- Provide a demo-local README with prerequisites, exact installation commands,
  configuration/authentication, start/stop, offline tests, live smoke test, replay,
  expected outputs, common failures and an explicit platform support statement.
- Define the minimal Python requirements from actual imports plus the team's
  requirements. Current known-good environment is Python 3.12; include the stage's
  `aiohttp` and other actual runtime dependencies rather than assuming the Spark
  venv already contains them. Put browser-test tooling in optional development deps.
- Keep the OT-2 simulator in its own environment. Reuse/reference the team's
  `execution/requirements-sim.txt` where appropriate: current pins are
  `opentrons==8.8.2`, `numpy<2`, with the tested OT-2 API ceiling 2.27.
- Keep Paperclip isolated; current version is GXL 0.8.16. Carry its install manifest,
  official source and hash verification instructions. The wheel URL is mutable:
  detect mismatches rather than silently upgrading. Explain device login/private
  API-key configuration without carrying anyone's authentication state.
- Carry OpenCode 1.19.5 installation/version/checksum information and the demo
  configuration. Pin the compatible SDK 2.0.41 and plugin 1.19.5. Verify dependency
  installation on first boot; do not rely on an ignored pre-populated node_modules.
  Verify supported architecture/downloads rather than assuming the Spark binary
  works on everyone's laptop. Document the Spark-hosted browser option.
- Replace hardcoded old workspace roots, sibling-repo paths, absolute `file://`
  provider URLs and old Python module names with derived/configurable locations.
  Isolate OpenCode cwd/config/tool discovery and private state within the demo so
  launching it does not alter other contributors' agent setup.
- Include safe example configuration and demo-local ignore rules. Never copy or
  commit `.env` contents, OAuth tokens, keys/passwords, OpenCode auth/session DBs,
  existing venvs, node_modules, model checkpoints or unrelated private logs. Install
  dependencies reproducibly; require each collaborator's own credentials or their
  authorized access to the existing server. Do not require local Qwen/GPU downloads
  for the default Nebius demo; document Qwen as an optional path.

## Completion checks

- [ ] Changes are isolated on the team demo branch; other workstreams and their
  ongoing modifications are preserved. No push, main merge or slide deployment.
- [ ] A clean environment can follow the README and install the actual dependencies.
  Running from a different filesystem location does not require the Ouroboros repo,
  its hidden state or old absolute paths. Document any untested OS/architecture.
- [ ] Offline evidence/pipeline tests pass; the Nebius compatibility adapter remains
  active and its usage/limitations are documented. No unannounced provider changes.
- [ ] The migrated UI completes a bounded retrieval → proposal → compilation →
  simulation rehearsal with the same clearly labeled software fixture, or records
  exactly which live dependencies prevented verification. No manual substitution
  may be presented as autonomous success.
- [ ] Evidence, selected-run plate/source details, status, downloads, saved replay,
  desktop/mobile layout and the existing slide/demo entry point still work.
- [ ] Memory, TODOs and installation instructions are discoverable within `demo/`,
  linked without external workspace paths, and distinguish measured proof from
  remaining work. Leave a short dated migration summary and verification results.

The earlier TODOs (real biological case, bacterial KG integration, stronger evidence
review, agent budgets and reliability work) remain valid but are **not prerequisites
for simply moving the verified demo into its agreed repository home**.
