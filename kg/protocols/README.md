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
| [`templates/`](templates/) | the curated templates: step tree (steps, and sub-steps where the evidence holds the detail), parameters with every observed value, controls, readout, exemplar AIDs. **Agent-curated, not yet human-checked** |
| [`conditions.yaml`](conditions.yaml) | 15 routing conditions, each read off an archetype's own `purpose` text (quote per edge), 3 with a machine-checkable expression |
| [`rules.yaml`](rules.yaml) | 18 AGM design rules, each with a verbatim quote, the chapter's NBK ID, and a machine-checkable expression where one exists (6 of 18) |
| [`pubchem.py`](pubchem.py) | PUG-REST + Entrez client: candidate AIDs per archetype, one AID's protocol text and tested series; on-disk cache in `data/raw/pubchem/` (git-ignored), ≤ 5 req/s, retries |
| [`extract.py`](extract.py) | LLM extraction of one AID's protocol text into the pydantic schema (closed verb set, units normalized in code, provenance per field), via `wwtn.llm.chat`. **Never run for real: no API key here**; unit-tested with a stubbed client |
| [`build_db.py`](build_db.py) | assembles everything into `graph/nodes.csv` + `graph/edges.csv` in the [kg/README.md](../README.md) format |
| [`graph/`](graph/) | the built graph, committed: 140 nodes / 353 edges |
| [`tests/`](tests/) | 45 tests, no network: two trimmed real PubChem JSONs in `tests/fixtures/` |

`seed.py` (three hand-written templates) is gone: `build_db.py` replaces it and writes the same `graph/` folder,
with `APPLICABLE_TO`, `ANSWERS`, `HAS_PARAM`, `MEASURES`, `HAS_STEP`, `NEXT` and `USES` unchanged, so
`kg.query.templates(target)` keeps working. Added since: `Rule` nodes with `HAS_RULE` (Protocol → Rule) and
`APPLIES_TO` (Rule → Protocol); then `Condition` nodes with `REQUIRES` / `PREFERRED_WHEN` (Protocol → Condition)
and `HAS_SUBSTEP` (Step → Step).

## The tree

It is a **shallow decision tree**, three levels deep, all of it in the node/edge CSVs:

```
Protocol --ANSWERS--------> QuestionType   (qtype:potency)
         --APPLICABLE_TO--> TargetClass    (chembl_class:1100)
         --REQUIRES-------> Condition      (cond:recombinant_enzyme_available)
         --PREFERRED_WHEN-> Condition      (cond:no_convenient_activity_assay)
         --HAS_STEP-------> Step 1 --NEXT--> Step 2 --NEXT--> ... --NEXT--> Step n
                                              |--HAS_SUBSTEP--> Step 2.1
                                              |--HAS_SUBSTEP--> Step 2.2
```

1. **Which templates could answer this?** `ANSWERS` (question type) and `APPLICABLE_TO` (the target's class
   chain) — what `kg.query.templates(target)` already did.
2. **Which of them fits this question and this lab?** `REQUIRES` (without it the template cannot be run) and
   `PREFERRED_WHEN` (what makes it the better choice), to `Condition` nodes. This was implicit in the agent's
   prompt; now a proposal can cite the condition it relied on, and a reviewer can read the branch. A
   `Condition`'s `check` is an expression over a design (`wwtn.schema.Experiment` fields plus whatever context
   the caller passes), evaluated by `build_db.check_condition` exactly like a rule's; 12 of 15 are `null`,
   because what a lab can do, or what the question asks, is an *input* to routing rather than something an
   `Experiment` can answer.
3. **Right stage, right detail.** `HAS_STEP` + `NEXT` give the ordered stages, as before. A step that spells out
   more than one operation now owns `HAS_SUBSTEP` children (`<protocol>/step4/sub1`, a `Step` node with a
   `parent` prop), so a grading tree can score the stage and its detail separately. Only 5 steps of the 3
   curated templates are split, into 10 sub-steps — the ones whose own `evidence` already held the detail; each
   sub-step keeps a parent quote or a span inside one (`tests/test_tree.py` checks that), and the rest stay flat
   rather than invent a shape.

```bash
python -m kg.query conditions proto:kinase_binding_competition   # the branch: REQUIRES first
python -m kg.query steps proto:bacterial_mic_broth               # the step tree, sub-steps indented
```

## Rebuild / use

```bash
python -m kg.protocols.build_db                 # rewrite graph/nodes.csv and graph/edges.csv
python -m kg.protocols.build_db --check         # summary only, writes nothing
python -m kg.query templates Q13627             # the templates that apply to DYRK1A, via its class chain
python -m kg.query conditions proto:cell_viability_atp                # when that template is the right one
python -m kg.query steps proto:cell_viability_atp                     # its steps, with their sub-steps
python -m kg.protocols.pubchem candidates proto:kinase_biochem_lum    # needs network; caches under data/raw/
python -m kg.protocols.pubchem show 623998                            # one AID's protocol text and series
python -m pytest -q kg                          # 84 tests, no network (1 GPU test skipped)
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

## Adding a condition

1. Find the sentence in `archetypes.yaml` that already says it (`purpose` or `notes`). If no archetype text says
   it, the condition does not go in the graph: say it in `archetypes.yaml` first, with its AGM chapter, and only
   then read it off. A condition is a *routing* fact ("purified enzyme is available"); a design rule from the AGM
   ("at least 10 concentrations") belongs in `rules.yaml` instead.
2. Add an entry to `conditions.yaml`: `id` (`cond:<name>`), `text`, `check` (an expression over an `Experiment`,
   or `null`), and one `from` entry per archetype that cites it — `archetype`, `field`, `relation` (`REQUIRES` or
   `PREFERRED_WHEN`) and a `quote` that is a verbatim span of that field, whitespace-normalized. One entry = one
   edge; reuse an existing condition across archetypes rather than writing a near-duplicate.
3. `python -m kg.protocols.build_db` and `python -m pytest -q kg/protocols`; `test_tree.py` fails if a quote is
   not in the archetype it names.

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
- **`extract.py` has never seen a real model.** Prompt and retry are only exercised by the stub, and it has no
  `substeps` field yet (`TODO(final)`): an extracted template arrives flat, so the sub-steps of the five
  archetype-only templates have to be split by hand or the extractor's schema extended.
- **The conditions are a reading of the archetype text, not a reviewed list.** `REQUIRES` vs `PREFERRED_WHEN` is
  this branch's judgement ("when X is available" → requires, "use for / an alternative when" → preferred), and a
  condition exists only where some archetype says it: `proto:kinase_biochem_trfret` is also a purified-enzyme
  assay, but its `purpose` does not say so, so it carries no `cond:recombinant_enzyme_available` edge. Fix the
  archetype text first, then the edge follows.
- **Hold-out hygiene.** `pubchem.candidates` drops AIDs deposited in or after `kg.constants.CUTOFF_YEAR`, but the
  curated templates were picked by hand; all exemplars are 2008-2014 depositions, well before the cutoff.

References: AGM (NBK53196; chapters read from the NCBI open-access archive, since the web pages answer scripts
with a reCAPTCHA), PubChem PUG-REST and Entrez `db=pcassay`, BAO via OLS4, ChEMBL protein classification REST.
