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

Rules: keep every node's and edge's `source` (provenance is what makes the proposals verifiable); normalize units in
code (µM, µL, min, °C); tag assay types and readouts with BioAssay Ontology (BAO) IDs where one exists.
