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
| [`rules.yaml`](rules.yaml) | 19 AGM design rules, each with a verbatim quote, the chapter's NBK ID, and a machine-checkable expression where one exists (7 of 19) |
| [`pubchem.py`](pubchem.py) | PUG-REST + Entrez client: candidate AIDs per archetype, one AID's protocol text and tested series; on-disk cache in `data/raw/pubchem/` (git-ignored), ≤ 5 req/s, retries |
| [`extract.py`](extract.py) | LLM extraction of one AID's protocol text into the pydantic schema (closed verb set, units normalized in code, provenance per field), via `wwtn.llm.chat`. **Never run for real: no API key here**; unit-tested with a stubbed client |
| [`defaults.py`](defaults.py) | how a parameter's **default** is chosen from its observations: one reference exemplar for the concentration series, nearest-to-centre for the rest, canonical snapping for fold-spacings, a derivation and a dispersion flag on every default (see below) |
| [`build_db.py`](build_db.py) | assembles everything into `graph/nodes.csv` + `graph/edges.csv` in the [kg/README.md](../README.md) format |
| [`graph/`](graph/) | the built graph, committed: 140 nodes / 353 edges |
| [`tests/`](tests/) | 74 tests, no network: two trimmed real PubChem JSONs in `tests/fixtures/` |
| [`graph/`](graph/) | the built graph, committed: 141 nodes / 367 edges |
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

## How a default is chosen

A template parameter records **every value seen across the exemplar assays**, each with its AID (or file) and a
verbatim quote, and none of them is marked as the default. Picking one used to be `observed[0]` — "the exemplars
are listed most-canonical first", which nothing enforced or recorded, so the default was really "whichever assay
happens to be listed first" (that is how `dilution_factor` defaulted to 2.97-fold over an equally valid 3-fold,
and `top_concentration` to 12 µM out of 10 / 12 / 46 / 46 µM). [`defaults.py`](defaults.py) derives it instead,
and every `Parameter` node carries the derivation next to its `value`, `unit`, `aid`, `quote` and `observed`.

Four rules, in this order:

1. **Reference run** for the parameters that describe *one* concentration series — `top_concentration`,
   `bottom_concentration`, `dilution_factor`, `n_points`, plus any parameter a template marks `"series": true`.
   Aggregating them one at a time can assemble a series nobody ever ran (one assay's top with another's spacing
   need not span what it should), so **all of them come from a single exemplar**: of the exemplars that report
   the *whole* series, the one whose series sits closest to the centre of all exemplars. Distance per parameter
   is `|log10(value / centre)|` for multiplicative quantities (concentrations, fold-spacings) and
   `|value - centre|` for counts, each divided by that parameter's own median absolute deviation so one
   parameter cannot dominate, then summed. Ties go to the exemplar the template lists first, and the losing
   candidates' totals stay in `reference_run_candidates`.
2. **Nearest to centre** for every other numeric parameter (volumes, times, temperatures, cell counts, …): the
   observation closest to the centre of that parameter's observations, after converting them to one unit (2 h
   and 120 min are the same observation). The default is always a value some exemplar really used — a mean or a
   median nobody ran is never written out. Ties go to the most frequently observed value, then to the exemplar
   listed first.
3. **Modal value** when any exemplar states the parameter in words ("room temperature", "overnight"): the value
   the most exemplars state verbatim, since words cannot be ordered against numbers without inventing a
   conversion.
4. **Canonical snapping** for fold-spacings, as a tie-break and an artefact fix: a chosen spacing within **5 %**
   (relative) of a member of `{2, 2.5, 3, 3.162, 4, 5, 10}` is snapped to it, and `snapped`, `snapped_from` and
   `snapped_to` record that. This is what makes the number executable — 2.97-fold is a rounding artefact of
   reading concentration columns, 3-fold is a transfer a pipette can do. Outside the tolerance the observed
   value is **kept and flagged** `off_ladder` rather than forced onto the ladder.

The **centre** is the geometric median for multiplicative quantities (in one dimension, the median of the logs)
and the ordinary median for linear ones; `centre`, `centre_unit` and `centre_rule` say which was used.

**The dispersion flag.** `exemplars_disagree` is `true`, and the derivation text says so, when the exemplars
genuinely disagree rather than scatter: at least a decade of spread on a log-scale parameter (`wide_spread`), a
spread wider than the centre itself on a linear one, a chosen value more than half a decade from the centre
(`chosen_far_from_centre`), or numbers and words mixed in one parameter (`mixed_value_kinds`). In the three
curated templates that is 10 of 39 parameters — e.g. the kinase template's `atp_stock_concentration` (20–903 µM,
because ATP is chosen per kinase) and the viability template's `cells_per_well` (500–5000). A reader who needs
one of those should read `observed`, not the default.

A parameter with observations but **no** derivable default (no observations at all, an observation attributable
to neither an AID nor a file, units from different dimensions in one parameter, a non-positive value on a log
scale) raises `DefaultError` and the build fails. Nothing silently resolves to element zero.

```python
from kg.protocols.build_db import load_templates
from kg.protocols.defaults import resolve_parameters
props = resolve_parameters(load_templates()["proto:kinase_biochem_lum"])
print(props["dilution_factor"]["value"], props["dilution_factor"]["derivation"])
# 3.0 reference run: all of dilution_factor, n_points, top_concentration come from one exemplar, aid:588811 ...
```

What this changed in the curated templates: the kinase series now comes from AID 588811 as a whole (12 µM,
3-fold — snapped from 2.97 — 9 points; the 46 µM of 623998/623999 is the top of two *interleaved* series and
neither AID reports a spacing or a point count, so neither can be a reference run), its
`kinase_reaction_time` is 60 min rather than 2 h, its `kinase_reaction_temperature` "room temperature" rather
than 28 °C, and the MIC template's `plate_wells` 96 rather than 384 (flagged: the exemplars say 96, 96, 384).

## Rebuild / use

```bash
python -m kg.protocols.build_db                 # rewrite graph/nodes.csv and graph/edges.csv
python -m kg.protocols.build_db --check         # summary only, writes nothing
python -m kg.query templates Q13627             # the templates that apply to DYRK1A, via its class chain
python -m kg.query conditions proto:cell_viability_atp                # when that template is the right one
python -m kg.query steps proto:cell_viability_atp                     # its steps, with their sub-steps
python -m kg.protocols.pubchem candidates proto:kinase_biochem_lum    # needs network; caches under data/raw/
python -m kg.protocols.pubchem show 623998                            # one AID's protocol text and series
python -m pytest -q kg                          # 113 tests, no network (1 GPU test skipped)
python -m pytest -q kg                          # no network (1 GPU test skipped)
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

### The analog anchor rule

`rule:agm/anchor_series_on_analogs` binds the template's generic series *shape* to the measured *scale* of the
query compound's structural analogs: the top concentration should be the analogs' median IC50 times the series'
own centring multiplier (`dilution_factor ** ((n_points - 1) / 2)`), within one dilution step, so half the
points sit above the expected potency and half below. It is **machine-checkable**, over an `Experiment` plus one
context value, `analog_median_ic50_uM` — which `agent/anchor.py` computes deterministically from
`bio_kg_analogs` and supplies through `Anchor.rule_context()`, together with the analogs it used. With no
analogs the context value is missing, so the check returns `None` (a judge item), which is the right answer:
there is then nothing measured to centre the series on and the template default stands.

The multiplier *follows from* the chapter's half-above/half-below sentence plus the template's shape; the AGM
chapters cited here state **no numeric multiplier** of their own, and the familiar "100x the expected IC50"
rule of thumb is a heuristic, not an AGM number (`TODO(final)` on it in the rule text and in `agent/anchor.py`).
The rule is a default a proposal may depart from with a stated reason, not a hard constraint.

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
evidence, not invention. Which of them becomes the default is derived, with its reason recorded on the node:
"How a default is chosen".

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

- **Human check of the curated templates.** Agent-curated (`TODO(final)` in each file). The quotes are
  verbatim; the defaults are now *derived* and each carries its derivation ("How a default is chosen"), so what
  needs reviewing is the rule rather than 39 individual judgements — above all the thresholds (5 % snapping
  tolerance, one decade of spread for the dispersion flag) and whether a reference run should be allowed to fall
  back to a partial-coverage exemplar. The 10 parameters flagged `exemplars_disagree` want a human to pick, not
  a rule.
- **Source diversity is low.** The kinase template is four Broad MLPCN assays + one NCGC qHTS; the viability one
  is four Scripps assays; the MIC one is three AIDs from one Scripps project. The parameter ranges are narrower
  than the field's.
- **The MIC archetype's target class.** Organisms have no ChEMBL protein class; it currently points at
  `chembl_target_type:ORGANISM`, which the biology graph does not define. Agree the bridge ID.
- **Two BAO IDs we did not find.** No OLS term for a kinase competition-binding *format* beyond
  `BAO:0003032` (method), and none for "cellular thermal shift"; the target-engagement archetype uses the
  NanoBRET kit term instead.
- **Rules are design rules, not QC.** 12 of 19 are judge items (Z', MSR, Km, DMSO, enzyme concentration) because
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
