# The demo page

One query through the whole pipeline, as a timeline: the knowledge base says "I don't know" → the agent queries
the two graphs → reasons → proposes the missing experiment → writes the procedure and the OT-2 script → the
proposal is checked against the record held out of the KB.

It is static: it plays **traces**, one file per query in `runs/`. Today there is one, a **mock**
(`runs/kit_imatinib.js`, marked as such on the page). When the pipeline runs for real, it writes the same trace
and the page shows the real run: no change to the page.

**Owner:** professorduckydoo (turning it into the real thing). <!-- TODO(final): confirm owner -->

- **Open:** `demo/index.html` (works from disk; self-contained, fonts in `fonts/`), or `demo/` next to the live deck.
  It is also embedded as the "Live demo" slide.
- **Where it lives:** here, at the repo root, so work on it does **not** redeploy the slides (the deploy workflow
  only runs for changes under `slides/`). The deck reaches it through a symlink, `slides/talks/biohack/demo ->
  ../../../demo`, which `slides/tools/build_site.sh` follows (`cp -rL`), so every slides deploy publishes the
  current demo. To publish demo changes without touching the slides, run **Deploy slides** by hand (GitHub ->
  Actions -> Deploy slides -> Run workflow). Keep `index.html` at this path: the slide embeds
  `demo/index.html?theme=dark`.
- **URL options:** `?all` (every stage at once), `?run=<id>`, `?theme=dark|light`.
- **Add a query:** add `runs/<id>.js` and a `<script>` tag for it in `index.html`. A `.js` file, not `.json`,
  because browsers won't `fetch` from `file://`.

## Trace format

`runs/<id>.js` calls `(window.DEMO_RUNS = window.DEMO_RUNS || []).push({...})` with:

| field | what |
| --- | --- |
| `id`, `query`, `model`, `mock` | the question; `mock: true` shows the "illustrative" badge |
| `lookup` | `{tool, args, result, verdict, note}`: what the KB says on its own |
| `calls` | the graph tool calls, each `{tool, args, summary, rows, columns?}` |
| `reasoning` | list of strings |
| `proposal` | the `ExperimentProposal` of `wwtn/schema.py` (`experiment`, `citations`, ...) |
| `procedure`, `protocol`, `simulation` | the steps, the OT-2 script, `{ok, detail}` from `opentrons_simulate` |
| `plate` | `{rows, top_uM, factor, points, controls}` for the plate map |
| `validation` | `{held_out, truth, checks: [[text, passed], ...]}` against the held-out record |

## Making it real

1. **Real traces, same page (do this first; lowest risk).** Have the pipeline (`agent/`, the KG queries in
   `kg/query.py`, `execution/`) record the pieces above as it runs, and a small exporter write them as
   `runs/<id>.js` (from `agent/out/<run>.jsonl` + `execution/out/<run>/`). Set `mock: false`; the badge goes away.
   Add a `<script>` tag per trace in `index.html`. Nothing else on the page changes.
2. **Live queries (optional).** A small backend (e.g. FastAPI) that runs the pipeline for a typed question and
   returns one trace as JSON. Change `find()` in `demo.js` to `fetch` it (falling back to the recorded traces when
   the backend is unreachable), and stream stages as they finish if you like: `playStage` already plays one stage
   at a time. Serve the backend from a GPU box behind a tunnel (Brev or Cloudflare, see DISCUSSIONS.md) and test it
   from outside the network before the talk.
3. **Keep the recorded traces** as the demo-day fallback whatever happens with the live mode.

Pacing (how long each stage "works", reading pauses) is set by the constants at the top of `demo.js`.
