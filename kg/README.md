# kg/: the two knowledge graphs

| Folder | Graph | What it holds |
| --- | --- | --- |
| [`biology/`](biology/) | biology KG | compounds, targets, target classes, known activities: a small subset around our questions |
| [`protocols/`](protocols/) | protocol KG | experiment templates (assay type, steps, parameters, controls, readout) and the AGM design rules |

Both graphs use **one file format**, so the agent can load and join them the same way.

## Format

Each graph writes two CSV files to its folder's `graph/` (committed, so the agent can use them without rebuilding):

`nodes.csv`

| column | example |
| --- | --- |
| `id` | `CHEMBL941` (use the source's own ID: ChEMBL, UniProt, BAO, ...; make up `proto:...` IDs only for our own nodes) |
| `type` | `Compound`, `Target`, `TargetClass`, `Protocol`, `Step`, `Parameter`, `Reagent`, `Labware`, `Readout`, `Rule`, `Condition`, ... |
| `name` | `imatinib` |
| `props` | a JSON object for anything else: `{"value": 10, "unit": "uM"}` |
| `source` | where it came from: `ChEMBL 35`, `hand-curated`, `LLM-extracted from CHEMBL1234567` |

`edges.csv`

| column | example |
| --- | --- |
| `src`, `dst` | node IDs (either graph's) |
| `rel` | `INHIBITS`, `MEMBER_OF`, `HAS_STEP`, `HAS_SUBSTEP`, `NEXT`, `USES`, `HAS_PARAM`, `MEASURES`, `APPLICABLE_TO`, `ANSWERS`, `HAS_RULE`, `APPLIES_TO`, `REQUIRES`, `PREFERRED_WHEN`, ... |
| `props` | JSON, e.g. `{"ic50_nM": 120}` |
| `source` | as for nodes |

**The bridge between the graphs** is `TargetClass` (kinase, protease, GPCR, ...): biology has
`Target -MEMBER_OF-> TargetClass`, protocols have `Protocol -APPLICABLE_TO-> TargetClass`. Agree on those IDs early.
The seed graphs use ChEMBL's protein classification: `chembl_class:<protein_class_id>`, chained with `SUBCLASS_OF`
(e.g. `chembl_class:1100` = Protein Kinase, under `chembl_class:6` = Kinase).

Rules: keep every node's and edge's `source` (provenance is what makes the proposals verifiable); normalize units in
code (µM, µL, min, °C); tag assay types and readouts with BioAssay Ontology (BAO) IDs where one exists.

### Design rules as nodes

The protocol graph also holds the NCATS Assay Guidance Manual's design rules as **`Rule`** nodes
(`rule:agm/<name>`), so a proposal can be checked against the rules that apply to the template it chose:

| edge | meaning |
| --- | --- |
| `Protocol -HAS_RULE-> Rule` | this rule applies to this experiment type (`props.severity`: `must` or `should`) |
| `Rule -APPLIES_TO-> Protocol` | the same link the other way, so a `Rule` node can be walked from either side |

A `Rule`'s props carry the AGM chapter (`agm_chapter`, `agm_nbk`, `url`), a verbatim `quote` from it, and `check`:
an expression over the fields of `wwtn.schema.Experiment` that `kg.protocols.build_db.check_rule` evaluates
(`True`/`False`), or `null` for the rules only a judge can score. See
[`protocols/README.md`](protocols/README.md).

### Routing conditions and nested steps

The protocol graph is a shallow decision tree, not a flat list of templates: besides `APPLICABLE_TO` (the target
class) and `ANSWERS` (the question type), a `Protocol` hangs off **`Condition`** nodes (`cond:<name>`) that say
when it is the right choice, and a `Step` may own one level of sub-steps:

| edge | meaning |
| --- | --- |
| `Protocol -REQUIRES-> Condition` | without this the template cannot be run at all |
| `Protocol -PREFERRED_WHEN-> Condition` | this is what makes it the better choice among the candidates |
| `Step -HAS_SUBSTEP-> Step` | one level of detail under a top-level step; `HAS_STEP` and `NEXT` stay at the top level, so the ordered chain is unchanged |

Every routing edge carries the `quote` from the archetype text it was read from, and a `Condition`'s props carry
`text`, `derived_from` (archetype, field, quote) and `check`: the same kind of expression as a `Rule`'s, or
`null` when only the lab or the question can answer it. Sub-step nodes are `Step` nodes with a `parent` prop; a
top-level step has none. See [`protocols/README.md`](protocols/README.md).

## Querying

`kg/query.py` loads both graphs (`kg/graph_io.py` reads and writes this format) and answers typed lookups that
return node IDs, so anything built on them can cite its sources:

```bash
python -m kg.query resolve KIT              # find nodes by ID, name or a target's ChEMBL ID
python -m kg.query activities P10721        # a target's IC50s, most potent first, with assay and paper
python -m kg.query summary P10721           # n, min, median, max IC50: a crude concentration-range prior
python -m kg.query templates P10721         # protocol templates that apply, via the target's classes
python -m kg.query classes P10721           # the target's class chain
python -m kg.query conditions proto:kinase_biochem_lum   # when that template is the right one
python -m kg.query steps proto:kinase_biochem_lum        # its steps, with their sub-steps
```

From Python: `from kg.query import KG; kg = KG.load()`, then `kg.resolve`, `kg.neighbors`, `kg.classes`,
`kg.activities`, `kg.potency_summary`, `kg.templates`, `kg.conditions`, `kg.steps`. `kg.nodes_df` / `kg.edges_df` are the pandas frames and
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

- **Seeds, not the real graphs.** Whatever `kg/biology/build_seed.py` builds is a stand-in for the kg/biology
  owner's graph. `kg/protocols/graph/` is now built by `kg/protocols/build_db.py` from real sources (PubChem AIDs
  and the AGM), but only 3 of its 8 archetypes have a curated template, and those are **agent-curated, not yet
  human-checked** (see `kg/protocols/README.md`, "Open questions").
- **The biology seed covers 19 kinases** (`kg/biology/README.md` lists them, with what curators should check).
- **Activity filters** (`kg/biology/chembl_db.py`, checked on the real ChEMBL 37 dump): IC50s with an exact `=`
  value in nM, no validity flag (or "Manually validated"), wild-type assays only (mutant variants dropped).
- **Smaller gaps:** a missing document row would leave a dangling `FROM_DOC` edge; `KG` assumes every `INHIBITS`
  edge has `ic50_nM`; one error message covers unknown and non-human target IDs; targets carry no gene name; there is
  no optional held-out pair list (the cutoff year is the only hold-out).
