# Demo workstream

The current judge demo is the Ouroboros planner and prepared-results viewer on
Brev. Start with the [judge runbook](docs/JUDGE_RUNBOOK.md),
[current memory](memory/MEMORY.md), and [setup](SETUP.md).

- Private operator: loopback port 7100; prepared judge view: loopback port 7200.
- Default: GLM-5.3 with low reasoning effort, 16,384 output tokens and bounded tool
  attempts. Three consecutive autonomous rehearsals passed, producing eight
  simulator passes. The verification checkpoint has 34 passing tests.
- Biology lookup reads the real ChEMBL bacterial graph. Rehearsal assay settings
  are explicitly synthetic; literature retrieval and simulator runs are real.
- The supplied robot video is a fixed 30-second recording, independent of the
  generated protocols. It is labelled recorded, not a live feed.
- Public access remains closed. Do not start another launcher alongside the
  systemd services, publish the operator, or deploy slides as part of this setup.

## Legacy slide-linked demo

The sections below document the preserved `index.html` trace viewer and
`agent.server` interface. They are historical/alternative entry points, not the
current judge configuration or a description of the planner's graph data.


One query through the whole pipeline, as a timeline: the knowledge base says "I don't know" → the agent queries
the two graphs → reasons → proposes the missing experiment → writes the procedure and the OT-2 script → the
proposal is checked against the record held out of the KB.

It plays **traces**, one file per query in `runs/`, and can also run the agent **live** (below). Today
`runs/kit-imatinib.js` is a real run of `agent/propose.py` (the LLM's tool calls, reasoning and proposal; the
graphs behind it are still the hand-written sample in `agent/data/sample_kg`), and `runs/kit_imatinib.js` is the
original **mock**, kept because it is the only trace with the execution and validation stages. A stage whose data
a trace lacks is skipped.

**Owner:** professorduckydoo (turning it into the real thing). <!-- TODO(final): confirm owner -->

- **Open:** `demo/index.html` (works from disk; self-contained, fonts in `fonts/`), or `demo/` next to the live deck.
  It is also embedded as the "Live demo" slide.
- **Where it lives:** here, at the repo root, so work on it does **not** redeploy the slides (the deploy workflow
  only runs for changes under `slides/`). The deck reaches it through a symlink, `slides/talks/biohack/demo ->
  ../../../demo`, which `slides/tools/build_site.sh` follows (`cp -rL`), so every slides deploy publishes the
  current demo. To publish demo changes without touching the slides, run **Deploy slides** by hand (GitHub ->
  Actions -> Deploy slides -> Run workflow). Keep `index.html` at this path: the slide embeds
  `demo/index.html?theme=dark`.
- **Stepping:** a stage plays, then waits for **Next step** (pressed mid-stage, it finishes that stage first);
  **Show all** plays the rest at once.
- **Figures:** two inline SVGs drawn from the trace itself, so they follow the run and the theme: after the graph
  calls, the subgraph the agent touched (compound and analogs, target, class, protocol, with the missing
  compound → target edge dashed); with the proposal, the concentration series on a log axis against the
  analogs' IC50s. Both come from `calls[].rows` and `proposal.experiment`; no extra trace fields.
- **URL options:** `?all` (every stage at once), `?auto` (play on without waiting for Next step), `?run=<id>`,
  `?theme=dark|light` (the button at the top right also switches it, and remembers the choice in the browser).
- **Add a query:** `python -m agent.propose --question "..." --id <id> --runs-js demo/runs` writes `runs/<id>.js`;
  add a `<script>` tag for it in `index.html`. A `.js` file, not `.json`, because browsers won't `fetch` from
  `file://`.

## Live mode

```bash
python -m agent.server                 # then open http://localhost:8008/talks/biohack/demo/ (or /demo/)
python -m agent.server --model moonshotai/Kimi-K3 --record demo/runs
```

`agent/server.py` serves `slides/` (with this folder mounted at `/talks/biohack/demo/` and `/demo/`) and, behind
`/api/`, runs the agent on a typed question and streams the trace to the page stage by stage (server-sent
events), so the tool calls and the reasoning appear as the model produces them. When the page finds the backend it
shows a "Run live" switch (on by default) and a model dropdown (`wwtn.llm.EVAL_MODELS` plus the server's default;
`--models a,b,c` changes the list); the suggestion buttons still play the recorded traces. A question already run
is replayed from the server's cache (`?fresh` reruns), and `--record` writes every finished run as a
`runs/<id>.js`, so a rehearsed live run doubles as a recorded one. If the backend fails before anything is shown,
the page falls back to the recorded trace. The deck's "Live demo" slide embeds the page from the same origin, so it
is live too when the deck is opened from `http://localhost:8008/talks/biohack/`. On the public (static) deck there
is no backend, so the page plays the recorded traces.

## Trace format

`runs/<id>.js` calls `(window.DEMO_RUNS = window.DEMO_RUNS || []).push({...})` with:

| field | what |
| --- | --- |
| `id`, `query`, `model`, `mock` | the question; `mock: true` shows the "illustrative" badge |
| `note` | shown as a badge: e.g. which graphs the run used |
| `lookup` | `{tool, args, result, verdict, note, rows?}`: what the KB says on its own. `kind` splits the `I don't know` verdict for the benchmark's abstain metric: `no_measurement` (both sides resolved, the pair is genuinely unmeasured) or `unresolved` (the KB does not know the compound or the target); `answered` otherwise. Added field, nothing renamed |
| `calls` | the graph tool calls, each `{tool, args, summary, rows, columns?}` |
| `reasoning` | list of strings, the model's visible reasoning between tool calls; `thinking` holds the raw reasoning tokens when the model exposes them (not shown) |
| `proposal` | the `ExperimentProposal` of `wwtn/schema.py` (`experiment`, `citations`, ...) |
| `anchor` | the deterministic concentration anchor (`agent/anchor.py`): `top_concentration_uM`, `series_uM`, `median_ic50_nM`, `multiplier` + `multiplier_basis`, the `analogs` it used (node ID, IC50, similarity), `skipped`, `confidence` + `flags`, `template_default_uM`, and whether the model `followed` it with any `departure_reason`. Absent when no anchor was computed (no experiment, or no usable analog). Added field, nothing renamed |
| `procedure`, `protocol`, `simulation` | the steps, the OT-2 script, `{ok, detail}` from `opentrons_simulate` |
| `plate` | `{rows, top_uM, factor, points, controls}` for the plate map (derived from the proposal by `agent/trace.py`) |
| `validation` | `{held_out, truth, checks: [[text, passed], ...]}` against the held-out record |

`agent/propose.py` fills everything through `proposal`/`plate` (`agent/trace.py` is the writer). Still to hook
up: `execution/` for `procedure`, `protocol`, `simulation` and `benchmark/` for `validation`; the natural place
is for them to add to the same trace (JSON in `agent/out/traces/<id>.json`) before it is written as `runs/<id>.js`.

## Historical next steps for the legacy trace viewer

These are legacy plans, not authorization to publish or change the active demo.

1. Point the agent at the real graphs (`kg/query.py`, branch `kg-scaffolding`) instead of `agent/data/sample_kg`,
   and rerecord `runs/kit-imatinib.js`.
2. Feed `execution/` and `benchmark/` into the trace; then drop the mock.
3. Keep recorded traces as the demo-day fallback, whatever happens with the live mode. For a public live demo,
   serve `agent.server` from a GPU box behind a tunnel (Brev or Cloudflare, see DISCUSSIONS.md) and test it from
   outside the network before the talk.

Pacing (how long each stage "works", reading pauses) is set by the constants at the top of `demo.js`.

## Ouroboros planner (consolidated runtime)

The portable planning/execution backend now lives in `demo/harness/`. Start with
[installation and operation](SETUP.md), [architecture](harness/PIPELINE.md), and
[current memory and TODOs](memory/MEMORY.md). `demo/index.html` and the slide symlink
remain the original static/agent.server entry point; the OpenCode planner is served
on port 7100 by its own launcher. These are explicit alternatives, not two loops
running for one question. The planner's `/legacy` page uses the legacy `stage` agent
only when launched with `STAGE_AGENT=stage`; the default is `planner`.

For public-access preparation and the private-operator/read-only-viewer boundary,
see [deployment notes](deploy/README.md). The current operator interface is shared
and must not be published as a multi-user application.

## Sequential recorded walkthrough

The results viewer now also serves `/sequential`: select one of its approved
recordings, then follow saved retrievals, proposals, compiler checks and simulation
reports with automatic pacing, pause/resume, Next step, Show all and Replay.
It uses only the existing published-session allowlist and read-only artifact APIs.
No new model call, private transcript, or physical execution is triggered. Timing
is illustrative and milestones are reconstructed from saved artifacts, not an
exact agent transcript. Synthetic assay inputs and scientific limitations remain
visible. The original `index.html` and slide entry point are preserved.

The sequential LLM dropdown uses `sequential-models.json`: four team evaluation
model IDs, plus a verified session-to-model mapping. It filters already published
sessions; missing models show a not-ready state, never another model's output.
To add a precomputed trajectory, run the chosen model privately through the operator,
verify the result and model identity, publish the reviewed session through the existing
viewer allowlist, and add its exact session/model pair to this manifest. Restart
only the viewer when its session allowlist changes. The dropdown itself never runs
inference or changes the operator's model. Current mapped examples are GLM-5.3.
