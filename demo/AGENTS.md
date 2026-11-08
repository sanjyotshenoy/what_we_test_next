# Demo workstream

Read `SETUP.md`, `memory/MEMORY.md`, and `docs/PIPELINE_TODO.md` first.
Keep implementation and private state within demo/. Shared contracts, execution,
KG and slides remain team-owned: adapt here, do not modify those folders.
Preserve index.html and the slide symlink. No push or main merge without a request.
Run Python modules from repository root as `demo.harness.*`. Never use a parent
workspace venv, credentials or absolute paths. Install with `python3 demo/install.py`.
No secrets in Git or output. Keep fixture/saved/live/physical evidence distinct.
At milestones update memory/MEMORY.md and docs/11-08-2026.md; record decisions in
../DISCUSSIONS.md. The old external harness is historical, not the active source.
