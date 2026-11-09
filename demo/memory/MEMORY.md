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

Desktop layout: agent on the left; KG above the molecule pane in the middle;
plate, generated protocol/video and simulator stacked in the right column. Mobile
places the molecule pane immediately after the KG.

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

## Agent workflow map — 2026-11-08

The agent pane now renders seven clickable blocks: protocol context; biological
and literature evidence branches; experiment design; design checks; generated
protocols; simulation. This is a conceptual map of saved artifacts, not a claimed
parallel execution trace. Counts derive from the selected session. Review-needed
rules remain amber; simulation passes require the viewer's verified report as well
as the manifest status. A missing report never earns a verified badge.

Click/Enter opens a formatted detail dialog with inputs/results, proposals,
provenance, rule review requirements or artifact downloads. Close/Escape returns
focus to the block; Escape closes a dialog without also exiting pane focus mode.
Session changes clear the old map/details. New files: dashboard-workflow.js/css.

Verification: the workflow browser test exercised all seven blocks across all eight
trajectories, downloads, keyboard focus, mobile dialog bounds and a missing-report
case. It and the existing pane browser regression passed. Deployed map and proposal
dialog were visually inspected. No writes, inference or service restart required.

## Browser asset freshness — 2026-11-08

After the user reported the old workflow list, the running origin was confirmed to
serve the new workflow code, but static assets lacked explicit revalidation headers.
The operator now serves HTML with `Cache-Control: no-store` and content-hashed `?v=`
URLs for every local JS/CSS file. Static assets use `no-cache` (revalidate, including
304 responses). Asset versions update automatically when their bytes change.
This addresses stale browser assets; the user's exact cached state was not observed.
The public judge viewer remains a separate application. Nine cache/API/workflow
tests passed before reloading the idle operator. No agent session was interrupted.

## Public dashboard and visitor keys — 2026-11-08

The public demo root now serves the six-panel operator dashboard. `/sequential`
remains unchanged; `/results` preserves the previous read-only results view.
`/planner` is a dedicated visitor-key form. New results open in the same dashboard
via `/?run=...`, accessible only with the originating browser's HttpOnly cookie.

No saved Nebius credential is available to the public runner. Each run requires a
newly entered key, passed only over HTTPS and a stdin pipe to an isolated process.
The public service never connects to private OpenCode or its key profiles. Existing
private operator credentials remain private and are not changed by this deployment.
Worker environment excludes inherited provider keys and disables dotenv. The key
lives only in that worker's client; tool subprocesses do not inherit it. Public
runs use `wwtn.llm.chat` plus the existing six bounded demo tools, with JSON actions
and the existing planner prompt. This is a new transport, not a replay of OpenCode.

At most two concurrent public runs / one per browser, sixteen turns, fifteen
minutes. No automatic model retries. Stop kills the process group. Private run
artifacts expire after one hour; graceful shutdown removes them. Browser ownership
is in memory, so restart revokes access. Paperclip still uses the demo account.
Tests cover access boundaries, stdin key transport, cancellation, browser CSP,
workflow/molecule display, and key clearing/storage absence. No paid call was made.
TODO(final): Rehearse the public runner with a visitor-supplied Nebius key.

## Views and access

| View | URL | Behavior |
| --- | --- | --- |
| Sequential | https://demo-o10eetwuq.gobrev.dev/sequential | Public, precomputed model/query walkthrough |
| Public dashboard | https://demo-o10eetwuq.gobrev.dev/ | Approved artifacts; visitor-key live runs at `/planner` |
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

## Banner name — 2026-11-08

User chose **Ouroboros** (corrected spelling) for the top-left dashboard banner.
The saved operator dashboard and public visitor-key planner now use that name.
The sequential walkthrough and original demo entry point are unchanged.

## Live query presets — 2026-11-08

Public live planning now offers the same two questions as the precomputed runs:
ciprofloxacin against E. coli/P. aeruginosa, and ciprofloxacin versus tetracycline
hydrochloride against E. coli. Selection fills the editable prompt with the exact
canonical text from demo/examples, including supplied synthetic assay settings,
identities, provenance requirements and limitations. No duplicated prompt copy or
automatic inference is introduced. A resumed run restores its own question/model.
The browser regression verifies both full prompts and selected-prompt submission;
public boundary and worker tests remain in place.

## Live workflow and visible output — 2026-11-08

Starting a public run now opens its live dashboard automatically. The flowchart
populates as evidence and compiled/simulated artifacts arrive, with the active
backend stage highlighted. A separate Model output block represents generation;
the UI does not infer a tool stage before the model has selected it. Submission
emits actual validation/compilation progress. Queued, returned, rejected, stopped
and failed stages remain distinct; simulator verification still requires hashes.

The Live output tab receives visible assistant completion content incrementally,
plus tool input/result previews. Clicking Model output shows its current turn in a
live dialog; a draft proposal preview is available before compilation. Provider
reasoning fields, request metadata, credentials and transport exceptions are not
forwarded. Output is escaped/text-rendered, not executed. The isolated worker adapts
SDK streaming to the existing wwtn.llm.chat interface without changing wwtn/.
Incomplete/truncated streams are never dispatched as complete tool actions. No
retry, fake typing animation or fallback model was introduced.

Events stay in the run's owner-only in-memory state (up to 2,000 events / two million
text characters), use monotonic cursors, and expire with the existing run. Tool
previews are limited to 6,000 characters and explicitly marked when truncated.
Dashboard polls at one-second intervals and refetches final artifacts after a
terminal state. It preserves graph zoom, selected molecules, pane focus, open
output dialogs, and playback of an unchanged selected protocol. Long supplied
inputs are collapsed so the workflow remains visible. Stop is available directly
in the dashboard. The saved/sequential workflow remains read-only and unchanged.

Verification: 41 affected tests passed, including real tool progress/rejection,
streamed visible-content forwarding and reasoning-field exclusion, truncated
stream rejection, bounded event cursors, owner access, progressive stage/artifact
updates, output escaping, selection preservation and existing dashboard/browser
regressions. Provider output was mocked; no paid inference was performed.
TODO(final): Rehearse live streaming end-to-end using a visitor-supplied Nebius key.

## Dashboard light mode — 2026-11-08

Added a header Light mode / Dark mode toggle to saved and live dashboards. Dark
remains the default; the chosen theme is saved in browser localStorage under
ouroboros-dashboard-theme. Storage failures do not prevent switching themes.
Light styling covers workflow states, graph labels/edges/selection, tooltips,
dialogs, live output, plate roles and simulator activity. Cytoscape colors update
in place without rebuilding the graph or resetting zoom, selections or playback.

Deployed-origin Chromium checks passed for both themes, reload persistence, graph
colors/zoom, selected molecule preservation, workflow details and mobile width,
with no JS errors or write requests. Light screenshot visually reviewed. Static
assets update without a service restart; sequential assets remain unchanged.

## Visible live output, interruption and saved-trace switch — 2026-11-08

Live mode now keeps a compact model-output preview visible alongside the workflow.
It displays received chunk/character counts and the last output's run-relative
time; the connected indicator reflects successful polling, not invented model
activity. The Full activity log retains tool inputs/results and generated output.
Provider reasoning fields remain excluded. No token count is estimated or faked.

Interrupt run is now prominent in the top banner and remains accessible when a
pane is focused. It uses the existing owner-authorized worker cancellation API.
The banner also lists all published model/query traces. Selecting a saved trace
first interrupts an active run, then opens exactly that session/model with the
Precomputed label. If interruption fails, navigation is blocked and the live page
shows the failure; completed/stopped runs switch without another stop request.
Trace switching does not start inference or change the sequential walkthrough.

Verification: 16 relevant tests passed, including received-output display, live
interrupt, removal of active highlights, failed-stop navigation guard, cross-model
saved-trace selection, worker cancellation and existing dashboard behavior. These
are static UI changes; no service restart or paid inference was needed.

Deployed-origin mobile check also verified all eight published choices, fallback
from an expired run, and exact cross-model selection without writes or inference.

## Compact dashboard banner — 2026-11-08

The top banner now stays on one row. Reset layout and navigation live in a More
menu; at 1,100px and below, model/trace selectors and the theme toggle move into
that menu as well. Existing controls are moved, not cloned, so event handlers,
current values and live-run ownership remain intact. Interrupt run stays visible.
The menu supports outside-click dismissal and Escape with restored summary focus.

Deployed-origin browser checks covered widths 320–1920px, one-row header height,
menu bounds, selector/theme access and interrupt visibility without writes or
inference. Three existing layout/live/public browser regressions passed. Static
changes require no service restart; the sequential walkthrough is untouched.

## Dashboard title and fullscreen shortcut — 2026-11-08

Browser tab title is now exactly **Project Ouroboros - Dashboard** for saved/live
operator views. Press F (or Shift+F) to toggle browser fullscreen; More also has a
Fullscreen (F) button. The shortcut ignores typing in inputs, textareas, selects,
editable elements, composition/repeated keys and Ctrl/Meta/Alt combinations.
Fullscreen state updates the button label; unavailable browser support shows a
short message. Pane-focus Escape does not intercept an active fullscreen view.

Deployed Chromium checks verified the title, actual Fullscreen API entry/exit,
keyboard and menu operation, and typing/select guards with no JS errors or
inference. Static update only; sequential assets and running jobs are unchanged.

## Clickable Ouroboros home banner — 2026-11-08

The Ouroboros brand is now an accessible home link on the dashboard and public
planner. Normal navigation from an active live run first interrupts the owned run,
then returns to `/` with precomputed traces. If interruption fails, the current
page remains open and reports the failure. Expired/inactive runs can return home
without restarting inference. Modifier-click keeps normal browser link behavior.

Two browser regressions passed, covering keyboard activation, failed/successful
interruption before home navigation, planner return, and precomputed mode. This is
a static update with no service restart or paid inference.

## Provider-returned reasoning display — 2026-11-08

User requested reasoning traces only if a safe change could be completed within
five minutes. Added an optional, separate streaming callback for the provider's
explicit reasoning_content/reasoning string fields. New public workers enable it;
model prompts, request parameters, action parsing and completion text are unchanged.
No hidden provider data is requested or inferred. Other metadata/headers remain
excluded, and the default bridge without a callback still omits reasoning.

Live output now includes a labeled Provider reasoning section and an expandable
current-turn preview. Missing reasoning is explicitly shown as not returned, never
fabricated. Text is escaped and stays in the same bounded owner-only in-memory feed;
it is not written to credential files or Git. This supersedes earlier notes saying
all provider reasoning fields were excluded from the public display.

Sixteen relevant tests passed, including separate reasoning/content delivery,
unchanged completion JSON, metadata exclusion, output escaping and live controls.
No paid inference or service restart occurred. Only newly started workers gain the
callback; already-running sessions are left intact. Actual availability depends on
the model/provider response and remains subject to the existing paid-rehearsal TODO.

## Default reasoning visibility and trace following — 2026-11-08

Provider reasoning opens by default in live mode. New events scroll the reasoning
preview and full activity log to the latest text; opening either view also jumps
to its latest content. Idle polls do not force scrolling. Alternating reasoning
and output chunks create separate chronological log blocks. Provider availability,
model requests, ownership and cancellation behavior are unchanged.

Two browser regressions passed, including long streamed reasoning, default-open
state, bottom-of-log visibility and existing live controls. Static update only;
no service restart, active-run interruption or paid inference.

## Public dashboard admission cap — 2026-11-08

User requested a cap of 30 concurrent dashboard visitors. Public pages and data
APIs now share a cookie-based, in-memory admission gate: one slot per browser,
30-second visible-page heartbeat, and expiry after two minutes without requests.
Extra arrivals receive HTTP 429 and a busy page that retries every 15 seconds;
this is retry-based admission, not a FIFO queue. Multiple tabs share a slot.
The sequential walkthrough uses the same gate/heartbeat without editing its assets.
Static assets and health checks do not consume slots. Owned stop requests bypass
admission and request throttling while retaining existing authorization checks.
The previous 600/minute shared request budget is now per admitted visitor;
static dashboard assets are excluded. The existing two-live-run cap is unchanged.
Admission counts browser sessions, not verified people, and is single-process.
Closing a page releases its slot by timeout, not immediately. Browser sessions and
private results expire on viewer restart. No paid inference was performed.

Validation: public boundary, worker and browser regressions passed; a synthetic
100-arrival admission test returned exactly 30 successes and 70 busy responses.
Tests cover slot reuse, timeout reclamation, API gating, independent request
budgets and cancellation access. This is not a full dashboard capacity benchmark.

Deployment: restarted only wwtn-viewer after confirming zero active public
workers. Health and a deployed-origin Chromium check passed: saved runs rendered,
HttpOnly visitor cookie set, heartbeat successful, no browser JS errors. An initial
network-idle navigation check timed out; explicit page-readiness checks passed.
The full 100-arrival test ran against an isolated test server, not the live demo.

## Remove visitor inactivity expiry — 2026-11-08

User explicitly requested removing the two-minute dashboard session expiration.
Admission now defaults to no expiry; the 30-slot limit remains. Slots persist in
memory until viewer restart, even after a browser closes or loses its cookie.
The busy page states this behavior. This supersedes the previous idle-timeout
policy. Live-run execution limits and private-result retention are unchanged.
The regression advances admission time by one year, verifying all 30 reservations
remain and the original cookie still works while a new visitor is rejected.

Ten public-boundary tests passed. Deployed with zero active public workers;
wwtn-viewer is active and its health check passed. No inference was started.

## Dashboard visitor cap removed — 2026-11-09

User requested removing the 30-slot cap, documenting the change and committing.
Public dashboard, planner, results and sequential pages now admit visitors without
an occupancy limit or inactivity expiry. Removed the busy page, slot registry and
injected admission heartbeat. The old heartbeat asset is a no-op and its endpoint
remains compatible for already-open pages. Refreshing loads the current behavior.

The visitor cookie now serves only per-browser rate accounting (600 requests per
minute). Accounting older than one minute is discarded to avoid retaining an
unbounded history of visitors; this does not expire dashboard access. Live-run
limits remain two concurrent globally, one per browser, 20 starts/hour globally,
five starts/hour per browser, 16 model turns and 15 minutes. Owner checks, key
handling, cancellation and private-result expiry are unchanged. No shared code or
original sequential assets were edited.

Validation: 24 public-boundary, worker and browser tests passed. An isolated test
issued 100 simultaneous dashboard requests from cookie-free clients; all returned
200. This verifies removal of admission blocking, not full 100-user load capacity.
No paid inference was started. This supersedes the earlier visitor-cap policies.

Deployment: restarted only wwtn-viewer after verifying zero active public workers.
The deployed origin passed its health check and Chromium verification: saved runs
rendered, no admission heartbeat included, and no page JS errors. The initial probe
used an eval-based readiness check rejected by the existing CSP; the DOM-locator
probe passed without changing the CSP. No paid inference or push was performed.

## Fresh-device setup guide — 2026-11-09

Added demo/NEW_DEVICE_SETUP.md as the canonical fresh-host guide, linked from
README, SETUP, deployment docs and demo/AGENTS.md. The user explicitly invited a
repo-level agent note; root AGENTS.md now links it, and root CLAUDE.md already
imports AGENTS.md. No redundant project_guide file was introduced.

The guide separates Git-only historical replay, current saved dashboard, public
visitor-key runs and the optional private OpenCode operator. It documents Linux
ARM64 installer restrictions, locked environments, reviewed artifact export/import,
allowlist validation, optional media, per-host Paperclip authentication, key
isolation, foreground/systemd startup, HTTPS/ingress boundaries, current capacity
policies, verification and restart behavior. It explicitly identifies missing
ignored assets and the fact that new local commits are unavailable until pushed.

Verification: all embedded Python parsed; all eight session file sets and simulation
hashes validated. A relocated Git-only checkout rendered the four-protocol replay
and 96 wells with writes disabled. Exact export/import/allowlist snippets restored
eight sessions in temporary storage without credentials. Existing installed Python
dependencies were reused; a fresh full install and paid destination-host rehearsal
remain explicitly marked TODO(final). No production service restart or inference.

## Main integration — 2026-11-09

User authorized merging demo/judge-rehearsal and pushing main. Integration was
prepared in an isolated worktree on main 110dd06, merging demo tip 15c3dcc with a
real two-parent merge. Prior squash integration caused repeated add/add conflicts;
main had no subsequent demo changes, so the reviewed demo tree resolved those.
Main's non-demo tree was preserved exactly except the authorized root AGENTS.md
setup-guide pointer. Historical Opentrons additions and a deleted DISCUSSIONS.md
were not reintroduced; slides and benchmark files were unchanged.

Forty-two backend/browser regressions passed on the merged tree, using existing
Python environments and copied reviewed saved artifacts. No source-only skips,
paid inference or production restart. The saved-result/video archive remains
separate from Git and must be copied off the instance before it is deleted.

## IDEAL dashboard branding — 2026-11-09

User approved IDEAL: Integrated Development Environment for Autonomous Labs.
Project Ouroboros remains the broader scientific discovery project. The saved/live
dashboard and public planner now show IDEAL with the expanded subtitle and updated
accessible home labels. Dashboard tab title is IDEAL - Project Ouroboros Dashboard;
planner tab title is IDEAL - Live Planning. Subtitle truncates on narrow screens
so existing banner controls fit. README and the fresh-device guide explain the
project/dashboard naming distinction. Historical replay/sequential branding and
persistent preference keys were retained.

Three public/live/layout browser regressions passed. An isolated browser check
verified titles, subtitle and page/header bounds at widths 320, 390, 768, 1100,
1440 and 1920 on both pages; desktop screenshot was visually reviewed. Static
changes need no service restart or paid inference.

## First-visit dashboard help — 2026-11-09

Added an accessible first-visit IDEAL welcome dialog with the requested prototype
instructions, Nebius BYOK live-planning link, simulator Play-controls link and
focused robot-recording link. The recording is explicitly prerecorded and separate
from selected-protocol execution. A green Help button stays outside the More menu
and remains visible during panel focus and at mobile widths. Instructions use the
existing menu's live-planning URL so current live-session context is retained.

Closing via Close, Got it, Escape or a help link remembers dismissal using
ideal-dashboard-help-seen-v1 in browser localStorage. Storage failures are caught;
help still works, though automatic display can recur after reload. Simulator links
focus controls without starting playback; recording links select the recording tab
and focus its panel. Keyboard focus is restored appropriately. Small-screen brand
subtitles are hidden to keep Help and Interrupt available without banner overflow.

Four public/live/layout/workflow browser regressions passed, covering initial show,
remembered dismissal, reopening, panel destinations, playback controls, navigation,
and header/dialog bounds from 320px upward. A deployed-origin check also verified
storage-disabled fallback; the popup screenshot was visually reviewed. Updated the
fresh-device guide. Static-only deployment; no restart or paid inference.
