# Knowledge graph explorer

Static explorer for the current biology and protocol CSV graphs, joined by node ID.
Open `index.html` directly, or serve `slides/` and visit `/talks/biohack/graph/`.
The existing Cloudflare build includes this directory; its deployed URL is `graph/`
relative to the live deck. No extra service or CDN is needed.

Regenerate the snapshot from the repository root after graph changes:

```sh
python3 -m slides.tools.prep_graph_explorer
```

Search by name, ID or type; select a node; filter relationships; explore one or two
hops. At most 65 nodes are shown, with truncation reported explicitly. The inspector
preserves source records and properties; the relationship list exposes parallel
edges individually. Node/edge inspection uses text rendering, not source HTML.

Hiding an edge is a reversible, browser-memory-only exploration aid. It is not an
evaluation split: alternate paths and duplicate evidence may still expose the fact.
No held-out labels or scoring results are invented. Source caveats are displayed.
