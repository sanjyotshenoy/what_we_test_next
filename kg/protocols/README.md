# kg/protocols/: the protocol knowledge graph

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

Dose-response protocol templates as small typed graphs: `Protocol → Step → Parameter`, with the reagents, labware,
readout and endpoint each one uses, tagged with BioAssay Ontology (BAO) IDs and linked to target classes.

- **Start by hand:** 3 to 5 templates (biochemical enzyme inhibition, cell viability, binding), then enrich with LLM
  extraction from ChEMBL assay descriptions and protocols.io (retrieval only: its terms forbid training on it).
- **Steps** use a small verb set at the level of OT-2 API calls: `dispense`, `transfer`, `serial_dilute`, `mix`,
  `incubate`, `read`. Labware uses Opentrons `load_name`s.
- **Writes:** `graph/nodes.csv`, `graph/edges.csv` in the format in [../README.md](../README.md).
- **Run:** `python -m kg.protocols.build` _(to write)_

## Seed graph (in `graph/` now)

<!-- TODO(final): seed graph for testing; replace with the kg/protocols owner's graph. -->
`python -m kg.protocols.seed` writes three hand-written templates (`seed.py`): biochemical kinase inhibition
(luminescence), cell viability (cellular ATP) and kinase competition binding. Each has steps in the verb set above,
default parameters (10 µM top, 3-fold, 10 points, triplicate, 1% DMSO), DMSO and staurosporine controls, a readout,
an `ANSWERS -> QuestionType` edge and a plaintext `purpose`, and is `APPLICABLE_TO chembl_class:1100` (ChEMBL
"Protein Kinase"). Defaults are general knowledge, not taken from any 2024+ (held-out) paper.

References: BAO (IC50 `BAO:0000190`, concentration-response `BAO:0010258`), the Opentrons serial-dilution tutorial
(docs.opentrons.com/v2/tutorial.html), the Opentrons Protocol Library (github.com/Opentrons/Protocols), LabOP,
BioPlanner (arXiv 2310.10632), BioPIE (arXiv 2601.04524).
