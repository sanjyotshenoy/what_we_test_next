# kg/: the two knowledge graphs

| Folder | Graph | What it holds |
| --- | --- | --- |
| [`biology/`](biology/) | biology KG | compounds, targets, target classes, known activities: a small subset around our questions |
| [`protocols/`](protocols/) | protocol KG | dose-response protocol templates: steps, parameters, reagents, labware, readouts |

Both graphs use **one file format**, so the agent can load and join them the same way.

## Format

Each graph writes two CSV files to its folder's `graph/` (committed, so the agent can use them without rebuilding):

`nodes.csv`

| column | example |
| --- | --- |
| `id` | `CHEMBL941` (use the source's own ID: ChEMBL, UniProt, BAO, ...; make up `proto:...` IDs only for our own nodes) |
| `type` | `Compound`, `Target`, `TargetClass`, `Protocol`, `Step`, `Parameter`, `Reagent`, `Labware`, `Readout`, ... |
| `name` | `imatinib` |
| `props` | a JSON object for anything else: `{"value": 10, "unit": "uM"}` |
| `source` | where it came from: `ChEMBL 35`, `hand-curated`, `LLM-extracted from CHEMBL1234567` |

`edges.csv`

| column | example |
| --- | --- |
| `src`, `dst` | node IDs (either graph's) |
| `rel` | `INHIBITS`, `MEMBER_OF`, `HAS_STEP`, `NEXT`, `USES`, `HAS_PARAM`, `MEASURES`, `APPLICABLE_TO`, ... |
| `props` | JSON, e.g. `{"ic50_nM": 120}` |
| `source` | as for nodes |

**The bridge between the graphs** is `TargetClass` (kinase, protease, GPCR, ...): biology has
`Target -MEMBER_OF-> TargetClass`, protocols have `Protocol -APPLICABLE_TO-> TargetClass`. Agree on those IDs early.
The seed graphs use ChEMBL's protein classification: `chembl_class:<protein_class_id>`, chained with `SUBCLASS_OF`
(e.g. `chembl_class:1100` = Protein Kinase, under `chembl_class:6` = Kinase).

Rules: keep every node's and edge's `source` (provenance is what makes the proposals verifiable); normalize units in
code (µM, µL, min, °C); tag assay types and readouts with BioAssay Ontology (BAO) IDs where one exists.

## Querying

`kg/query.py` loads both graphs (`kg/graph_io.py` reads and writes this format) and answers typed lookups that
return node IDs, so anything built on them can cite its sources:

```bash
python -m kg.query resolve KIT              # find nodes by ID, name or a target's ChEMBL ID
python -m kg.query activities P10721        # a target's IC50s, most potent first, with assay and paper
python -m kg.query summary P10721           # n, min, median, max IC50: a crude concentration-range prior
python -m kg.query templates P10721         # protocol templates that apply, via the target's classes
python -m kg.query classes P10721           # the target's class chain
```

From Python: `from kg.query import KG; kg = KG.load()`, then `kg.resolve`, `kg.neighbors`, `kg.classes`,
`kg.activities`, `kg.potency_summary`, `kg.templates`. `kg.nodes_df` / `kg.edges_df` are the pandas frames and
`kg.graph` is a networkx `MultiDiGraph` of the same edges, for anything the methods don't cover.

## CPU or GPU

Graph building and querying are written once in pandas + networkx. CPU is the default and needs nothing extra.
For the GPU (RAPIDS: `cudf.pandas` and the `nx-cugraph` backend), install `kg/requirements-gpu.txt` and set
`WWTN_GPU=1` when starting Python, e.g. `WWTN_GPU=1 python -m kg.query templates P10721`; output starts with
`[gpu mode]`. The switch happens when `kg` is imported, so it must come before pandas or networkx is imported
(`kg/backend.py` refuses otherwise rather than silently running on the CPU). Inside graph frames `props` is kept as
JSON text, because cudf would turn a column of dicts into structs that give every row every key.
`kg/tests/test_gpu.py` checks that GPU mode gives exactly the CPU results; it is skipped when no GPU is visible.

## Known caveats

Each is also a `TODO(final)` comment where it lives (`grep -rn "TODO(final)" kg`).

- **Seeds, not the real graphs.** `kg/protocols/graph/` (three hand-written templates) and whatever
  `kg/biology/build_seed.py` builds are stand-ins for the kg/biology and kg/protocols owners' graphs.
- **No biology graph is committed yet.** `KG.load()` skips it with a warning until it is built from the ChEMBL dump.
- **Activity filters** (`kg/biology/chembl_db.py`, checked on the real ChEMBL 37 dump): IC50s with an exact `=`
  value in nM, no validity flag (or "Manually validated"), wild-type assays only (mutant variants dropped).
- **Smaller gaps:** a missing document row would leave a dangling `FROM_DOC` edge; `KG` assumes every `INHIBITS`
  edge has `ic50_nM`; one error message covers unknown and non-human target IDs; targets carry no gene name; there is
  no optional held-out pair list (the cutoff year is the only hold-out).
