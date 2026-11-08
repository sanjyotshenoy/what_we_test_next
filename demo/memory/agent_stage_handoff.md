> Historical source record (2026-11-07). Paths and status below describe the pre-migration implementation. Current instructions: [SETUP](../SETUP.md), [memory](MEMORY.md).

# Agent orchestration and stage handoff — 2026-11-07

**Latest priority:** First consolidate the working Ouroboros demo into
`what_we_test_next/demo/` on a separate branch, including required runtime dependencies,
installation instructions, documentation and memory. The user is on night duty and
wants to continue in one team repository without disturbing other workstreams.
Read [the consolidation plan](../docs/DEMO_CONSOLIDATION.md) first; it
supersedes the earlier separate-repository layout decision. Migration has not started.
Then use [the adaptable TODOs](../docs/PIPELINE_TODO.md); schemas and team
interfaces are expected to change. The evidence below describes the existing source.

## What now works

The new stage page drove the real OpenCode `planner` through all five tools:
`planning_context` → `literature_search` → `literature_read` → `planning_submit`
→ `planning_simulate`. No manually edited submission or direct backend substitute
was used in this final rehearsal. All four pair protocols passed (267 commands each).
The subsequent assistant message finished normally (`finish=stop`, no error).

This is **software integration evidence**, using two synthetic compound identities
and two synthetic species identities with explicitly supplied test parameters.
Paper retrieval, the team protocol/lab context, compilation and simulation were real.
It is not a reviewed real-species experiment, a measured MIC or a physical OT-2 run.

- Session: `ses_e46864406ffeAYxrmbT9XhIE2G`.
- Batch: `3b0d138f9d354335`.
- Team source commit: `5363a6f2e4236457af5e64e199d3a1079c28b52d`.
- Read citation: `paper:PMC10347090:L80-L110:d4715830dafe` (background only).
- Recorded assistant-call cost including final summary: $0.01670355, gpt-oss-120b.
- Ignored evidence: `harness/stage/check/planner-live-result.json`, `planner-live.png`,
  `planner-mobile.png`; protocols and reports under `harness/planning_runs/<session>/`.
  The screenshot/snapshot preceded the final answer; SQLite confirms final completion.

## Tool-call error and resolution

The bundled OpenAI-compatible SDK requires ID/name when a streamed tool starts.
A local buffering experiment handled delayed/numeric IDs in tests, but the live
Nebius stream sometimes omitted **both name and ID for the whole call**, returning
only two argument characters and `finish_reason=tool_calls`. Buffering cannot recover
that information. Do not guess the function name or manufacture its arguments.

Production Nebius adapter `.opencode/providers/nebius.mjs` now uses
`completeToolResponse` in `tool-stream.mjs`: request `stream=false` once, validate
complete function metadata/JSON arguments, normalize absent/numeric opaque IDs,
and adapt the result to the SDK's SSE interface. It makes no retry/model substitution.
OpenCode still owns the loop and tool execution. Text arrives per completed model
turn; tool/session events still update the UI. Usage is retained.

Pinned SDK: `@ai-sdk/openai-compatible` 2.0.41, OpenCode/plugin 1.19.5.
`.opencode/package.json` must be tracked despite the generated local ignore rule.
Launcher initializes dependencies before first provider use when SDK files are absent;
fresh-install behavior remains to be verified. Earlier streaming helper remains in
the module but is not the production path; cleanup and complete-response unit tests
are TODOs. The current stream test covers that earlier helper, not the new path.

The first complete-response run exposed a misleading validator error: correct
`experiment.controls`, but numeric `layout.control_columns` instead of labels.
Split field-specific errors and added schema/prompt descriptions; the final run
compiled on its first submission. That exact representation is current-contract
behavior, not a permanent schema decision. Earlier model corrections exceeded the
prompt's stated limit; enforce budgets in code later.

## Stage changes

`harness/stage/server.py` defaults to planner + cheap Nebius model. `/` serves the
new `planner.html/css/js`; `/legacy` retains the old seed-demo page. New read-only
planning/artifact routes expose actual session evidence, proposals, rule reports,
source identities, plate maps and simulator logs. `planning_view.py` invalidates a
pass badge when protocol/report hashes do not agree. Activity excludes reasoning.
Live and saved-artifact views are labeled; saved artifacts do not certify autonomy.
Requested rows and surplus technical wells remain distinct. No robot is connected.

Desktop (1600px) and mobile (390px) browser checks passed: 96 wells, 4/4 simulation
status, source display, well inspection, downloads, reload, run selection and saved
view; no JS errors or mobile horizontal overflow. Desktop screenshot inspected.
Eight pipeline tests + six evidence tests + one JS harness test (12 streaming
cases) pass. Dedicated stage API and complete-response regression tests remain TODO.

## Environment and handoff

Team repo synced cleanly from `6a189cd` to `5363a6f`; bacterial ChEMBL graph and graph
explorer merged. No team files modified. That new graph is NOT yet connected to the
planner. Previous records describing a kinase-only checkout are historical.

A `stage` tmux session on 4096/7100 was already running when checked. It was left
untouched; do not assume it loaded these new files. Temporary verification servers
used 4098/7102 and were stopped in a `finally` cleanup. Port check confirmed only
the pre-existing 4096/7100 listeners remain. No Qwen/container/hardware started.
Recheck running state next session. Restart the original stage deliberately when
ready to load the new code, after checking for an active user run.

An automatic approval review initially rejected external transmission of local
protocol/lab context. The user then explicitly approved the Nebius rehearsal;
subsequent live calls were within that approval. Credentials were not logged.

Consolidation is the next implementation task; other TODOs and the explanatory
walkthrough follow it.
No push. Preserve unrelated working-tree edits from earlier sessions.
