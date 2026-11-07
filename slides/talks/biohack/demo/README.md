# The demo page

One query through the whole pipeline, as a timeline: the knowledge base says "I don't know" → the agent queries
the two graphs → reasons → proposes the missing experiment → writes the procedure and the OT-2 script → the
proposal is checked against the record held out of the KB.

It is static: it plays **traces**, one file per query in `runs/`. Today there is one, a **mock**
(`runs/kit_imatinib.js`, marked as such on the page). When the pipeline runs for real, it writes the same trace
and the page shows the real run: no change to the page.

- **Open:** `slides/talks/biohack/demo/index.html` (works from disk), or `demo/` next to the live deck. It is
  also embedded as the "Demo" slide.
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

To hook up the pipeline: have `agent/` and `execution/` log these pieces as they run and write them out with a
small exporter (`agent/out/<run>.jsonl` + `execution/out/<run>/` → `runs/<id>.js`). For the "search engine"
version, serve traces from a backend and change `find()` in `demo.js` to fetch one.
