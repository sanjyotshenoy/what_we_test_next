# Demo memory — current checkpoint, 2026-11-08

Active branch: `demo/judge-rehearsal`. Runtime implementation commit: `0f946db`;
subsequent documentation commits record verification. No push or main merge was
requested or performed. Work stayed within `demo/`.

Start with the [judge runbook](../docs/JUDGE_RUNBOOK.md). The
[remote handoff](REMOTE_HANDOFF.md) retains the Brev/credential/history details;
its earlier default model and unstarted viewer descriptions are historical.

## What is ready privately

- Operator: `127.0.0.1:7100`, `wwtn-stage.service`.
- Internal OpenCode: `127.0.0.1:4096`, `wwtn-opencode.service`.
- Prepared judge view: `127.0.0.1:7200`, `wwtn-viewer.service`.
- All three are systemd-managed and enabled. No public listeners, proxy, TLS or
  firewall changes. Public access must stay closed until explicitly authorized.
- User chose a view-only judge experience while the team operates privately.
- User's fixed robot recording is locally prepared: 30 seconds, silent, 25.1×,
  H.264/720p. The UI labels it recorded and unrelated to the selected simulation.

Default planning model is now **Nebius `zai-org/GLM-5.3`**, temperature 0,
`reasoning_effort=low`, 16,384 output tokens, at most 16 model steps. Request metadata
confirmed these settings reach the provider. GPT-OSS remains a manual alternative;
there is no automatic model switch. The existing custom provider adapter remains
the documented exception to the shared `wwtn.llm.chat` convention.

The submission tool now exposes the validator's actual nested schema. Citation
rejections list exact retrieved IDs; validation remains strict. Truncation is an
explicit error. Busy runs reject additional prompts and key/model changes; model
changes start a new conversation. The UI restores controls after completion and
labels a stopped-before-compilation run distinctly.

## Verified

34 tests pass: 27 main/browser/transport/recording/boundary tests plus 7 evidence
checks. Fresh authenticated Paperclip searches and full-text reads succeeded
standalone and inside the autonomous loops. Browser checks verified desktop/mobile
layout, plate/run selection, downloads, video playback/seeking, and no JS errors.

Three consecutive autonomous rehearsals with the final GLM settings succeeded:

| Session | Case | Runs | Elapsed |
| --- | --- | ---: | ---: |
| `ses_e4584faa3ffe1IRLWBu4RnowCT` | Real graph identities, synthetic assay settings | 2 | 24.1 s |
| `ses_e45849c51ffeAj4a8dVLJkTK2M` | Synthetic 2×2 fixture | 4 | 33.1 s |
| `ses_e45830dcdffec6BtfRHpmnGmZo` | Real graph, operated through browser with video playing | 2 | 35.7 s |

All eight simulations passed (267 commands each). The fixture's first submission
was rejected for duplicate question IDs; the agent corrected it and succeeded
within the existing budget. No manual argument or artifact repair was performed.
These are software checks, not biological validation or physical execution.

The viewer allowlist contains the last two sessions above, with the real-graph
session first. Operator `DEMO_DEFAULT_SESSION` selects that same completed session
on startup. A fresh prompt still creates a fresh live session. Approved results,
rehearsal receipts and media are ignored local files, not supplied by a Git clone.

Earlier GPT-OSS failures and a GLM 8,192-token reasoning-limit failure are preserved.
One model run is not guaranteed to succeed; the prepared view works without live
LLM or Paperclip access. Do not retry a failed run without inspecting its outcome.

## Remaining scope

A reviewed biological question/strain, reference-protocol hardware review, four-
antibiotic single-plate compiler support, automated step-3 benchmark grading,
and public hostname/auth/TLS decisions remain open. The demo does not support
arbitrary experimental protocols. No local 5090 endpoint was identified.

- [Setup](../SETUP.md), [verification log](../docs/11-08-2026.md),
  [pipeline](../harness/PIPELINE.md), [remaining TODOs](../docs/PIPELINE_TODO.md).
- [Packaged historical replay](../replays/README.md) remains distinct from the new
  live runs; no physical robot is controlled by the app.

<!-- TODO(final): Domain review and external access decisions are still required
before describing this as a biological or publicly deployed production system. -->


## Documentation maintenance

The demo README now leads with the active judge configuration and labels the old
slide-linked trace workflow as legacy. `docs/PIPELINE_TODO.md` separates completed
software verification from pending scientific review and broader reliability work.
`SETUP.md` contains the full 34-test command set and uses a separate loopback port
for optional replay, avoiding the running operator. Historical failures remain in
the handoff and verification log. This documentation-only reconciliation did not
rerun paid rehearsals, restart services, or change access settings.

## Sequential playback addition

User requested a gradual multi-query walkthrough using Sanjyot's trajectories.
`/sequential` on the prepared viewer reconstructs milestones from its existing
approved sessions, with selectable recordings, pause/resume, speed, step, show-all
and replay. It does not expose private transcripts or broaden the session list.
The original slide-linked demo is preserved. Source is `sequential.html`,
`sequential.js`, `sequential.css`; served through explicit public-view asset routes.
Later access setup (after the historical checkpoint above): the judge viewer is
public via Brev HTTPS; the separate operator requires the current org-member email
allowlist. This change does not alter either access rule.

Sequential UI refinement: no header playback badge; new milestones scroll into
view, and long prose/detail blocks collapse at 100 words with expandable text.
Saved-result provenance remains in the introductory copy and session description.

Presentation language now describes example queries and the active workflow step,
not recordings or milestone counts. A compact precomputed-example provenance line
and expandable About note retain the distinction from fresh inference/physical
execution. No model selector is shown without corresponding model trajectories.

Removed per-step Example output badges. Added the four team evaluation models to
an LLM dropdown, backed by `sequential-models.json`. Only verified session/model
pairs are shown; currently GLM-5.3 has the two approved trajectories. Others show
not-ready. Changing selection cancels progression and clears the prior output.

User requested a presentation-only flow: removed Pause, Next step, Show all,
Replay, Speed and Explore full results controls. Selecting a query starts automatic
3.5-second milestone progression and scrolling; selecting another query/model
cancels the previous progression. Text expansion and model/query selection remain.

First sequential milestone is now Scientist’s query: a concise request reconstructed
from the saved compound, assay and panel, with supplied experiment inputs expandable.
Removed introductory explanatory copy and About this example. This is a display
summary of saved inputs, not a claim to quote the original user prompt verbatim.
