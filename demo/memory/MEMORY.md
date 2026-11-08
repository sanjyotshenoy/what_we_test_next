# Demo memory — current state

Verified 2026-11-08, approximately 12:06 America/New_York. This file and
[REMOTE_HANDOFF.md](REMOTE_HANDOFF.md) supersede the archived append-only notes.
Read `demo/AGENTS.md`; no project_guide.md was present. Work remains scoped to demo/.

## Workspace and continuity

Brev `biohackdemo`, host `brev-o10eetwuq`, checkout
`/home/ubuntu/what_we_test_next`, branch **demo/judge-rehearsal**. Latest runtime
checkpoint before this documentation update: `55d8759` (light-mode sequential UI).
The checkout was clean at inspection. Recheck before editing: remote users may
start new work. Do not reset, switch or overwrite unfinished work.

Companion implementation clone `/home/ruh/wwtn-sequential-demo` uses branch
`demo/sequential-replay`. Commits were transferred by Git bundle and cherry-picked
onto Brev; commit IDs therefore differ. `/home/ruh/what_we_test_next_demo` is the
older public-readiness clone. Original `/home/ruh/what_we_test_next` and others'
worktrees were not changed. At the user’s request, the full demo/judge-rehearsal branch was pushed to GitHub
after this reconciliation. No merge into main was performed. The repository now
lives at sanjyotshenoy/what_we_test_next; the old Git URL redirects.
GitHub main previously received consolidate-demo at `f329771`; do not assume it
contains this deployment. Brev's repo deploy key is read-only.

## Operator dashboard update — 2026-11-08

The operator root and `/legacy` now use the original six-panel dashboard layout
with the eight precomputed sequential trajectories. Model/query selection is
browser-local and read-only; it does not change or start the shared agent session.
The live planner remains at `/planner`. Graph measurements, SMILES identities,
proposal/evidence details, pair-specific plates, protocol downloads and hash-checked
simulator logs come from saved artifacts. The molecule panel now shows cached
ChEMBL 2D SVG structures and downloadable molfiles, with saved SMILES and source
provenance available in details. The physical video remains separate.

The graph opens on the entire bacterial compound–organism network (605 nodes,
2,675 grouped links representing all 42,240 measurements); assay/document records
are summarized on links. **Focus run** shows only the saved retrieved subgraph.
Hover reveals formatted node/edge details; tap pins the card, Escape dismisses it.
The overview is current KG context, distinct from evidence retrieved in a saved run.

**Generated protocol** now displays a 2D OT-2 deck schematic driven by each
hash-verified simulator command log. Play/pause, Step, Reset and the command slider
highlight referenced slots and plate wells (eight-channel commands highlight a
column). Timing is illustrative; this is command playback, not a physics simulation
or new simulator execution. Switching protocols/sessions stops playback.
**Robot recording** switches to the separate physical video.

Verification: 15 HTTP/browser regression tests passed; a separate Chromium check
covered all eight trajectories / sixteen protocol pairs, wells, downloads and
desktop/mobile layout with no JavaScript errors or write requests. The initial
plate overlap was corrected before the successful check. No paid inference ran.
Later graph/molecule/playback update: 16 regression tests passed, plus Chromium
checks for all eight trajectories, hover/pinning, overview/focus, both loaded
chemical images, command scrubbing, eight-well highlighting, playback cancellation,
recording switch and mobile width.

## Resizable panes and graph-selected molecules — 2026-11-08

Desktop dashboard dividers resize the three columns and row boundaries. Drag them,
or focus a divider and use arrow keys (Shift for larger steps). Sizes persist in
browser localStorage; **Reset layout** or double-clicking a divider restores defaults.
Each pane has **Focus / Restore**; Escape restores the dashboard. Focus preserves
loaded artifacts, graph selection and playback state. Mobile keeps stacked panels
with vertical resizing and supports the same focus/restore controls.

Clicking a Compound node in either graph view selects that exact identity in the
molecule pane, shows its graph SMILES and renders a 2D SVG locally using vendored
SmilesDrawer 2.0.0 (MIT; license/checksums alongside the script). No external image
request or inference is made. Organism nodes only show their information. **Run
compounds** restores the saved-run molecule gallery. Missing/invalid notation leaves
an explicit message and the original SMILES. Graph selections do not change the
experimental run or become new retrieved evidence. Two of 593 graph compounds
lack SMILES and explicitly show unavailable notation.

Verification: 17 regression tests passed, including the persisted browser test
`demo.harness.test_dashboard_layout` (skips without local saved trajectories).
Deployed static UI also passed resize/focus/molecule checks. No service restart,
write/inference request or external molecule request was needed.

## Views and access

| View | URL | Behavior |
| --- | --- | --- |
| Sequential | https://demo-o10eetwuq.gobrev.dev/sequential | Public, precomputed model/query walkthrough |
| Judge/results | https://demo-o10eetwuq.gobrev.dev/ | Public, approved artifacts and separate robot video |
| Operator | https://operator-o10eetwuq.gobrev.dev/ | Brev login; current two org-member email allowlist; shared live session |

The operator allowlist is a membership snapshot, not automatic future-member access.
No anonymous operator access. Internal OpenCode is never published. Forwarding,
ports, reboot limitations and health commands are in the handoff and deploy README.

## Sequential product decisions

Headline: **From a scientific question to a robot-ready protocol**. Light mode only.
User chooses an LLM and a scientific question; steps automatically progress, shimmer
while processing, and scroll both when the placeholder appears and when results
expand. No Pause/Next/Show all/Replay/Speed/full-results toolbar or per-step badges.
Text over 100 words has Show more/less. Compact precomputed provenance remains.
First step is Scientist’s query plus expandable supplied inputs.

Evidence links and clickable 96-well maps use saved artifacts. Wells preserve
concentration, volume, controls and surplus-row accounting. The standalone haspin
missing-link example was removed at user request; do not reintroduce it or claim
known MIC links are missing. The original demo/index.html and slide symlink remain.

## Questions, models and evidence

1. What minimum ciprofloxacin concentration inhibits growth of E. coli and
   P. aeruginosa? Design experiments rather than claim a new measured MIC.
2. Which inhibits E. coli at a lower concentration: ciprofloxacin or tetracycline
   hydrochloride? Design matched experiments rather than claim a measured winner.

All four models have both trajectories: GLM-5.3, Kimi-K3, Qwen3.8-27B and DeepSeek
V4-Pro-0813. Eight accepted sessions / sixteen protocol-hash-verified simulator
passes. Exact IDs and one Qwen failed attempt/retry are in
[PRECOMPUTED_EXAMPLES.md](../docs/PRECOMPUTED_EXAMPLES.md). Qwen's comparison retry
used an explicit object-format instruction; these are not controlled model scores.

Models really retrieved graph/literature evidence and generated/validated/simulated
protocols. Assay settings are supplied synthetic inputs; strains remain unspecified.
No physical execution or biological result is established by these simulations.
The fixed 30-second robot recording is separate and does not show execution of
these generated protocols. Robot-ready means an output for lab review, not hardware
or biological certification. Four-antibiotic reference integration remains pending.

## Files and operations

- `sequential.html`, `sequential.js`, `sequential.css`: UI; `sequential-models.json`:
  eight reviewed session/model mappings; exposed via explicit public-view routes.
- `harness/stage/public_view.py`: read-only server; `planning_view.py`: hash-checked
  snapshots; `demo/private/published_sessions.json`: ignored allowlist, currently ten
  sessions (eight new plus two original judge defaults).
- `examples/*.txt`: prompts; `python -m demo.harness.precompute_examples`: creates
  independent OpenCode sessions without changing the operator selection. It performs
  paid inference/retrieval; do not run merely to preview or test the UI.
- `harness/planning_runs/`, `private/precomputed/`, credentials and video are ignored
  VM state. A Git clone does not contain these. Never print or commit secrets.
- Update this memory when behavior changes; log milestones in docs/11-08-2026.md.

## Verification and remaining gaps

Historical full runtime suite: 34 tests passed before sequential work. After changes,
six public-boundary tests passed, and browser checks exercised all eight combinations,
plate details, model switching/cancellation, mobile width, text expansion, shimmer,
light mode under dark OS preference and scrolling after content reveal. Public HTTPS
page/catalog returned 200. Do not describe the old full-suite result as freshly rerun.

Codex managed remote daemon 0.167.0 is running with --remote-control; ChatGPT login
is valid. Phone-side reconnection was not tested. No daemon restart, pairing or
permission changes were made. All three demo services are active/enabled. Operator
forward socket is active but disabled at boot; viewer forward socket is enabled.
Reboot recovery was not tested. Scientific/domain/hardware review, strain selection,
independent-user live sessions, broad reliability/load testing and main integration
remain open. No production-certification claim.
