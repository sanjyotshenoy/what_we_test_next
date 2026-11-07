# The demo page

One query through the whole pipeline, as a timeline: the knowledge base says "I don't know" → the agent queries
the two graphs → reasons → proposes the missing experiment → writes the procedure and the OT-2 script → the
proposal is checked against the record held out of the KB.

It plays **traces**, one file per query in `runs/`, and can also run the agent **live** (below). Today
`runs/kit-imatinib.js` is a real run of `agent/propose.py` (the LLM's tool calls, reasoning and proposal; the
graphs behind it are still the hand-written sample in `agent/data/sample_kg`), and `runs/kit_imatinib.js` is the
original **mock**, kept because it is the only trace with the execution and validation stages. A stage whose data
a trace lacks is skipped.

- **Open:** `slides/talks/biohack/demo/index.html` (works from disk), or `demo/` next to the live deck. It is
  also embedded as the "Demo" slide.
- **Stepping:** a stage plays, then waits for **Next step** (pressed mid-stage, it finishes that stage first);
  **Show all** plays the rest at once.
- **Figures:** two inline SVGs drawn from the trace itself, so they follow the run and the theme: after the graph
  calls, the subgraph the agent touched (compound and analogs, target, class, protocol, with the missing
  compound → target edge dashed); with the proposal, the concentration series on a log axis against the
  analogs' IC50s. Both come from `calls[].rows` and `proposal.experiment`; no extra trace fields.
- **URL options:** `?all` (every stage at once), `?auto` (play on without waiting for Next step), `?run=<id>`,
  `?theme=dark|light` (the button at the top right also switches it, and remembers the choice in the browser).
- **Add a query:** `python -m agent.propose --question "..." --id <id> --runs-js slides/talks/biohack/demo/runs`
  writes `runs/<id>.js`; add a `<script>` tag for it in `index.html`. A `.js` file, not `.json`, because browsers
  won't `fetch` from `file://`.

## Live mode

```bash
python -m agent.server                 # then open http://localhost:8008/talks/biohack/demo/
python -m agent.server --model moonshotai/Kimi-K3 --record slides/talks/biohack/demo/runs
```

`agent/server.py` serves `slides/` and, behind `/api/`, runs the agent on a typed question and streams the trace
to the page stage by stage (server-sent events), so the tool calls and the reasoning appear as the model
produces them. When the page finds the backend it shows a "Run live" switch (on by default) and a model dropdown
(`wwtn.llm.EVAL_MODELS` plus the server's default; `--models a,b,c` changes the list); the suggestion buttons
still play the recorded traces. A question already run is replayed from the server's cache (`?fresh`
reruns), and `--record` writes every finished run as a `runs/<id>.js`, so a rehearsed live run doubles as a
recorded one. If the backend fails before anything is shown, the page falls back to the recorded trace. The
deck's "Demo" slide embeds the page from the same origin, so it is live too when the deck is opened from
`http://localhost:8008/talks/biohack/`.

## Trace format

`runs/<id>.js` calls `(window.DEMO_RUNS = window.DEMO_RUNS || []).push({...})` with:

| field | what |
| --- | --- |
| `id`, `query`, `model`, `mock` | the question; `mock: true` shows the "illustrative" badge |
| `note` | shown as a badge: e.g. which graphs the run used |
| `lookup` | `{tool, args, result, verdict, note, rows?}`: what the KB says on its own |
| `calls` | the graph tool calls, each `{tool, args, summary, rows, columns?}` |
| `reasoning` | list of strings, the model's visible reasoning between tool calls; `thinking` holds the raw reasoning tokens when the model exposes them (not shown) |
| `proposal` | the `ExperimentProposal` of `wwtn/schema.py` (`experiment`, `citations`, ...) |
| `procedure`, `protocol`, `simulation` | the steps, the OT-2 script, `{ok, detail}` from `opentrons_simulate` |
| `plate` | `{rows, top_uM, factor, points, controls}` for the plate map (derived from the proposal by `agent/trace.py`) |
| `validation` | `{held_out, truth, checks: [[text, passed], ...]}` against the held-out record |

`agent/propose.py` fills everything through `proposal`/`plate` (`agent/trace.py` is the writer). Still to hook
up: `execution/` for `procedure`, `protocol`, `simulation` and `benchmark/` for `validation`; the natural place
is for them to add to the same trace (JSON in `agent/out/traces/<id>.json`) before it is written as `runs/<id>.js`.
