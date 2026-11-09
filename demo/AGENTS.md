# Demo workstream

Read `memory/MEMORY.md`, `memory/REMOTE_HANDOFF.md`, `SETUP.md`, and
`docs/PIPELINE_TODO.md` first. Files ending `_HISTORY.md` and dated logs are
historical, not current operating instructions. No separate project_guide.md is used.
For new-device setup or migration, read [NEW_DEVICE_SETUP.md](NEW_DEVICE_SETUP.md)
before running installers. It is the canonical fresh-host procedure; keep its
commands and asset/credential boundaries current when changing the runtime.
Do not infer a complete deployment from a Git clone: current saved sessions and
robot media are ignored artifacts. Verify the destination architecture, reviewed
asset bundle and publication allowlist. Never copy credentials to reproduce a demo.
Keep implementation and private state within demo/. Shared contracts, execution,
KG and slides remain team-owned: adapt here, do not modify those folders.
Preserve index.html and the slide symlink. No push or main merge without a request.
Run Python modules from repository root as `demo.harness.*`. Never use a parent
workspace venv, credentials or absolute paths. Install with `python3 demo/install.py`.
No secrets in Git or output. Keep fixture/saved/live/physical evidence distinct.
At milestones update memory/MEMORY.md and docs/11-08-2026.md; record decisions in
../DISCUSSIONS.md. The old external harness is historical, not the active source.
