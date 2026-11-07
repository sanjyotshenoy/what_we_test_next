# kg/protocols/: the experiment/protocol template database

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

Generalizable experiment **types** ("templates"), assay-level (the *what*), not robot steps. One template answers
one kind of question about one kind of target, so the agent can route a question to a design, and the grader can
take the *skeleton* of its rubric tree from the template while the *values* come from the held-out paper or AID.

Two sources, as the team agreed (see DISCUSSIONS.md, "What each source is for"):

| Source | What it gives | Where it lands |
| --- | --- | --- |
| NCATS **Assay Guidance Manual** (AGM, NCBI Bookshelf [NBK53196](https://www.ncbi.nlm.nih.gov/books/NBK53196/)) | why each assay type exists, when to use it, and the design rules | `archetypes.yaml` purposes, `rules.yaml` |
| **PubChem BioAssay** confirmatory dose-response AIDs | real written protocols: steps, parameters, controls | `templates/*.json`, via `pubchem.py` / `extract.py` |

## What is here

| File | What it is |
| --- | --- |
| [`archetypes.yaml`](archetypes.yaml) | 8 archetypes: 5 kinase + **3 non-kinase negative controls** (GPCR cAMP, protease FRET, bacterial MIC). Per archetype: question type, applicable ChEMBL protein classes, BAO IDs, purpose, AGM chapters, PubChem search hints |
| [`templates/`](templates/) | the curated templates: step tree, parameters with every observed value, controls, readout, exemplar AIDs. **Agent-curated, not yet human-checked** |
| [`rules.yaml`](rules.yaml) | 18 AGM design rules, each with a verbatim quote, the chapter's NBK ID, and a machine-checkable expression where one exists (6 of 18) |
| [`pubchem.py`](pubchem.py) | PUG-REST + Entrez client: candidate AIDs per archetype, one AID's protocol text and tested series; on-disk cache in `data/raw/pubchem/` (git-ignored), ≤ 5 req/s, retries |
| [`extract.py`](extract.py) | LLM extraction of one AID's protocol text into the pydantic schema (closed verb set, units normalized in code, provenance per field), via `wwtn.llm.chat`. **Never run for real: no API key here**; unit-tested with a stubbed client |
| [`build_db.py`](build_db.py) | assembles everything into `graph/nodes.csv` + `graph/edges.csv` in the [kg/README.md](../README.md) format |
| [`graph/`](graph/) | the built graph, committed: 115 nodes / 326 edges |
| [`tests/`](tests/) | no network: two trimmed real PubChem JSONs in `tests/fixtures/` |

`seed.py` (three hand-written templates) is gone: `build_db.py` replaces it and writes the same `graph/` folder,
with `APPLICABLE_TO`, `ANSWERS`, `HAS_PARAM`, `MEASURES`, `HAS_STEP`, `NEXT` and `USES` unchanged, so
`kg.query.templates(target)` keeps working. New: `Rule` nodes with `HAS_RULE` (Protocol → Rule) and `APPLIES_TO`
(Rule → Protocol).

## Rebuild / use

```bash
python -m kg.protocols.build_db                 # rewrite graph/nodes.csv and graph/edges.csv
python -m kg.protocols.build_db --check         # summary only, writes nothing
python -m kg.query templates Q13627             # the templates that apply to DYRK1A, via its class chain
python -m kg.protocols.pubchem candidates proto:kinase_biochem_lum    # needs network; caches under data/raw/
python -m kg.protocols.pubchem show 623998                            # one AID's protocol text and series
python -m pytest -q kg                          # 73 tests, no network
```

Soundness checks from the rules:

```python
from kg.protocols.build_db import check_rule, load_rules
from wwtn.schema import Experiment
design = Experiment(assay_type="biochemical kinase activity", readout="luminescence (ADP-Glo)",
                    system="recombinant DYRK1A", top_concentration_uM=10, dilution_factor=3, n_points=10,
                    replicates=3, controls=["DMSO vehicle", "no-enzyme wells"])
context = {**design.model_dump(), "expected_ic50_uM": 0.05}   # the potency prior from the biology KG
for rule in load_rules():
    verdict = check_rule(rule, context)      # True / False, or None = a judge item for the grader
```

## Curated vs extracted

| Archetype | Template | Exemplar AIDs |
| --- | --- | --- |
| `proto:kinase_biochem_lum` (biochemical kinase, ADP-Glo) | **curated** | 588811, 602295, 623998, 623999, 686948 |
| `proto:cell_viability_atp` (cell viability, CellTiter-Glo) | **curated** | 1691, 1699, 1413, 1972 |
| `proto:bacterial_mic_broth` (MIC broth microdilution) | **curated** | 449774, 1503, 463100, 624097 + the team's `Opentrons/` protocol (on `main`) |
| `proto:kinase_biochem_trfret`, `proto:kinase_binding_competition`, `proto:kinase_cellular_target_engagement`, `proto:gpcr_camp_functional`, `proto:protease_fret_activity` | archetype only | — (search hints in `archetypes.yaml`) |

The three curated templates were read by hand from the AID text and written as JSON; `extract.py` is the path to
the rest once a Nebius key exists. Every parameter value carries the AID (or file) and the quoted span it came
from, and `observed` keeps *all* the values seen across the exemplars, not just the default — the ranges are
evidence, not invention.

## Adding an archetype

1. Add an entry to `archetypes.yaml`: `id`, `name`, `question_type`, `applicable_to` (verify the ChEMBL class ID
   at `https://www.ebi.ac.uk/chembl/api/data/protein_classification.json`), `bao` (verify every ID in
   [OLS4](https://www.ebi.ac.uk/ols4)), `purpose` + the `agm` chapters it paraphrases, and `pubchem.search`.
2. `python -m kg.protocols.pubchem candidates <id>` to see which AIDs the hints find; read 3-5 of them.
3. Either write `templates/<name>.json` by hand in the shape of the existing three (value + unit + AID + quote per
   observation), or run `python -m kg.protocols.extract <aid> --archetype <id>` once a key exists.
4. Add any archetype-specific rules to `rules.yaml` (with a verbatim AGM quote), rebuild, run the tests.

## Open questions

- **Human check of the curated templates.** Agent-curated (`TODO(final)` in each file). The quotes are verbatim;
  the judgement about which value is the *default* is not reviewed.
- **Source diversity is low.** The kinase template is four Broad MLPCN assays + one NCGC qHTS; the viability one
  is four Scripps assays; the MIC one is three AIDs from one Scripps project. The parameter ranges are narrower
  than the field's.
- **The MIC archetype's target class.** Organisms have no ChEMBL protein class; it currently points at
  `chembl_target_type:ORGANISM`, which the biology graph does not define. Agree the bridge ID.
- **Two BAO IDs we did not find.** No OLS term for a kinase competition-binding *format* beyond
  `BAO:0003032` (method), and none for "cellular thermal shift"; the target-engagement archetype uses the
  NanoBRET kit term instead.
- **Rules are design rules, not QC.** 12 of 18 are judge items (Z', MSR, Km, DMSO, enzyme concentration) because
  `wwtn.schema.Experiment` has no field for them. If the grader wants them deterministic, `Experiment` needs
  fields (ATP vs Km, DMSO %, enzyme concentration) — a shared-schema change, so it needs the team's OK.
- **`extract.py` has never seen a real model.** Prompt and retry are only exercised by the stub.
- **Hold-out hygiene.** `pubchem.candidates` drops AIDs deposited in or after `kg.constants.CUTOFF_YEAR`, but the
  curated templates were picked by hand; all exemplars are 2008-2014 depositions, well before the cutoff.

References: AGM (NBK53196; chapters read from the NCBI open-access archive, since the web pages answer scripts
with a reCAPTCHA), PubChem PUG-REST and Entrez `db=pcassay`, BAO via OLS4, ChEMBL protein classification REST.
