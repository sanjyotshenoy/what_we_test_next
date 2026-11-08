# Missing-link experiment design: 20-case diagnostic suite (v1)

Status: **draft for human audit**, not a validated benchmark. Generation results are recorded separately under `benchmark/runs/twenty-case-pilot/`.
<!-- TODO(final): domain reviewer must approve the step abstractions, case labels, assay comparability and rubric; verify cross-database source independence before a scored run. -->

## What is being tested

Given a question, reusable parameterized step cards and retained measurements, propose a scientifically sound experiment: choose an endpoint/system, assemble ordered steps, bind numerical parameters, cite support and identify unresolved conditions.

This extends the current agent contract: current `ExperimentProposal` has no structured steps. These pilot input packets specify an experimental output contract without modifying `wwtn/schema.py` or the agent. A current-agent baseline can be graded on assay and parameters; its referenced template can be checked separately, but must not be represented as agent-generated steps.

## Original three-case pilot

| Case | Query | Reviewer-only measurement | Reason |
|---|---|---|---|
| 1 | CHEMBL4278808 → haspin Q8TF76, biochemical inhibition | 14 nM, assay CHEMBL5357346, document CHEMBL5356937 | Low-concentration coverage; appropriate biochemical endpoint. |
| 2 | CHEMBL5426285 → HASPIN Q8TF76, biochemical inhibition | 1,225 nM, assay CHEMBL5378515, document CHEMBL5375979 | Same target and step family, different reference potency; avoid unjustified default reuse. The same sensible series can pass both cases. |
| 3 | CHEMBL3936761 → Rec-1 cell growth/viability (record associated with BTK Q06187) | 360 nM, assay CHEMBL5209939, document CHEMBL5209897 | Distinguish a cellular endpoint from purified-enzyme inhibition and target-specific causality. |

Numbers are copied from committed ChEMBL graph rows, not inferred or newly measured. Case 3's `INHIBITS` graph label obscures assay semantics: its description explicitly says CellTiter-Glo / growth inhibitory activity in Rec-1 cells. The question intentionally supplies that system; this is not a test of inferring the system from a vague question. Case 2's assay description does not establish that the ADP-Glo template exactly matches the measured assay. No case provides a verified complete reference procedure.

Cases 1 and 2 are related diagnostic examples, not independent samples for estimating generalization. Three manually selected examples are a rubric-development pilot, not enough for performance claims.

## Expansion to 20 cases

The original three input packets are unchanged, including their historical scores and limitations. Cases 4–20 extend the original pilot. All 20 now have five-model outputs; see `benchmark/runs/twenty-case-pilot/RESULTS.md` for generation diagnostics, receipt accounting and limitations. The suite has **15 biochemical and 5 cellular cases**, **15 target IDs**, 20 distinct query compounds (also distinct exact stored SMILES), and pairwise-disjoint held-out document-ID sets. This is still a diagnostic collection, not a representative or statistically independent sample of all experimental design.

Selection was fixed without model outputs: first select four named cellular assays with different systems/readout challenges; choose the lexicographically first eligible compound ID in each. Then consider biochemical targets by descending eligible-record count (ties by target ID), excluding the original haspin/BTK targets; select one query for each of 13 targets. Within each target, sort by compound ID then assay ID and take the first candidate with a positive finite IC50, a previously unused query compound/SMILES, and a held-out document closure disjoint from all previously selected cases. Assay eligibility is type B / single-protein BAO_0000357, which is **not sufficient proof of inhibition-readout comparability**. Selection is not potency-ranked and does not ensure balanced potency bins. The explicit frozen IDs are in `slides/tools/benchmark_case_specs.json`; rebuilding uses these IDs, never silently substitutes new cases.

The cellular assays, in selection order, are CHEMBL5719093 (RPMI-8226), CHEMBL4822427 (AXL-expressing BaF3), CHEMBL5133843 (TMD8), and CHEMBL4834280 (MER-expressing BaF3). They appear as cases 17–20. Their retained examples require the specified system terms and a cellular growth/proliferation/viability endpoint; the checks do not establish identical exposure, construct, readout or culture conditions. Cases 17–19 have no eligible retained examples. Case 20 has five, which still require compatibility review. New cases exclude comparator compounds with the query's exact stored SMILES; salt/stereochemistry normalization and chemical-family independence are not established.

Important reviewer challenges:

- Case 5's recorded 305,000 nM is a weak reference activity, **not advice to dose at 305 µM**. Solubility, toxicity and assay feasibility may make abstention or a bounded range more appropriate than covering it.
- Case 9's description mixes binding and enzyme-inhibition assays; the metadata does not establish an inhibition-specific reference. Its numerical scientific comparison is not assessable until reviewed. Do not score exact reference coverage as validated success.
- Cases 17 and 20 use proliferation readouts; the provided CellTiter-Glo card cannot be copied as if it were their recorded procedure. Case 19 lacks sufficient procedure details. Supported adaptation or explicit unresolved conditions is expected.
- Different document IDs do not establish different underlying papers, chemical scaffolds or laboratories. Cross-database duplicates and source independence still require human audit. All five cellular cases must avoid target-specific causal conclusions from viability alone.

`cases/manifest.json` records suite version, input SHA-256 values, source hashes, case modes and retrieval counts. All numerical scientific comparisons remain marked **not established** until assay comparability is reviewed. Historical pilot scores cover cases 1–3; a subsequent blinded Astra-medium pass covers all 100 responses under a frozen three-axis rubric. See `benchmark/judge/RESULTS.md` for provisional AI scores and per-case evidence, and `benchmark/judge/PROMPT.md` for the exact prompt. These are not expert-validated scientific scores. Existing paid pilot runners remain pinned to those three; the separate expanded runner has completed the 20-case matrix, with costs recorded in its receipt ledger. Rebuilding this dataset makes no calls.

Each case must run in a **fresh, isolated context**, without previous cases, outputs or reviewer answers. Exclusions are per-case, not a suite-wide training/test split; a source hidden in one case may be legitimate context in another. Never train or tune on the reviewer bundle and then claim held-out evaluation. The UI remains an auditor interface only.

Offline validation: `python3 -m unittest slides.tools.test_benchmark_cases` checks reference provenance against raw edges, full document/assay closure, absence of excluded IDs in inputs, distinct queries/document groups, step prerequisites, packet hashes and preservation of original pilot inputs.

### Added case inventory (reviewer only)

| Case | Target / system | Held-out IC50 (nM) | Source document |
|---|---|---:|---|
| 4 | Tyrosine-protein kinase Mer | 76 | CHEMBL5212743 |
| 5 | Tyrosine-protein kinase receptor UFO | 305000 | CHEMBL4840343 |
| 6 | Aurora kinase A | 2000 | CHEMBL5149994 |
| 7 | DNA-dependent protein kinase catalytic subunit | 230 | CHEMBL1765064 |
| 8 | Serine/threonine-protein kinase mTOR | 10 | CHEMBL4811304 |
| 9 | Activin receptor type-1 | 8 | CHEMBL3886963 |
| 10 | Dual specificity tyrosine-phosphorylation-regulated kinase 1A | 410 | CHEMBL1155389 |
| 11 | Mitogen-activated protein kinase 9 | 320 | CHEMBL1154277 |
| 12 | Interleukin-1 receptor-associated kinase 1 | 39 | CHEMBL5678804 |
| 13 | LIM domain kinase 1 | 252 | CHEMBL1255531 |
| 14 | Mitogen-activated protein kinase kinase kinase 7 | 80 | CHEMBL3351803 |
| 15 | Casein kinase I isoform alpha | 1040 | CHEMBL1800061 |
| 16 | NUAK family SNF1-like kinase 1 | 840 | CHEMBL1153318 |
| 17 | human RPMI-8226 cells | 5444.3 | CHEMBL5715952 |
| 18 | mouse BaF3 cells expressing recombinant human AXL | 9 | CHEMBL4819114 |
| 19 | human TMD8 cells | 1.6 | CHEMBL5131445 |
| 20 | mouse BaF3 cells expressing MER | 4900 | CHEMBL4831559 |

All values above are reviewer-only reference measurements, not recommended settings or exact-match answers. This suite remains kinase/cell focused; it does not add MIC cases.

## Reproducible construction and exclusions

Run from repository root:

```sh
python3 -m slides.tools.prep_benchmark_cases
```

The generator reads `kg/biology/graph/{nodes,edges}.csv` and hashes those files plus the protocol graph CSVs. Each review record stores the hashes, IDs, counts and structural assertions. It does not modify either KB.

For each case independently:

1. Find **every** `INHIBITS` edge for the query compound/target pair, not only the selected measurement. Collect all their document IDs.
2. Exclude those Document nodes and every Assay linked to those documents by `FROM_DOC` or activity properties.
3. Exclude every edge touching those nodes, referencing those documents/assays in its properties, or measuring the query pair. This removes other compounds' results from the same documents too.
4. From surviving edges, retrieve at most five measurements on the same target from distinct other compounds. Sort by compound ID then assay ID and take the first eligible record per compound. Biochemical cases require assay type B and single-protein BAO_0000357; the original cellular case requires both `rec-1` and `viability` in the assay description (case-insensitive). New cellular cases use the explicit system terms in the frozen specification and require cellular BAO_0000219 plus a growth/proliferation/viability endpoint. Include the description so reviewers can assess actual comparability. **These examples are not structural analog rankings.** No aggregation, potency-based selection or query-value-based ranking is used.
5. Create a strict input allowlist: question; query entity IDs/names/types/SMILES where available; seven step cards; selected retained measurement records; generic guidelines; output contract. Raw documents, assay nodes, protocol nodes, parameter nodes, source quotes, full graph data and reviewer records are not model input.

For this snapshot, case 1 removes 24 edges, case 2 removes 44, and case 3 removes 144. Cases 1/2 have five retrieved measurement examples each; case 3 has none. Case 3 therefore tests suitability and honest handling of insufficient numerical evidence; do not demand an unsupported precise potency estimate. Rebuilt counts in review JSON are authoritative if the source changes.

These are **within-snapshot leave-pair-and-supporting-documents-out** cases, not the project's existing post-2024 temporal split. Apply the filtering separately for each case; all variants/baselines for a case receive the same input.

## Step abstractions and numbers

The seven cards are reviewer-authored abstractions informed by `proto:kinase_biochem_lum` and `proto:cell_viability_atp`, plus a generic analysis card. They are not an automatic lossless transformation of the protocol graph. Both step families are offered in every case so the model must choose an appropriate route. Suggested prerequisites constrain ordering; alternatives require justification.

Exact source-specific amounts, concentrations, times and temperatures are replaced by named slots in these cards. Original step text, quotes and parameter defaults are not copied into the input. Numeric measurement examples from independent retained records remain available deliberately: they are contextual evidence, not withheld answers. Card template IDs are provenance labels, **not permission to fetch the unfiltered templates**.

The cards do not encode a complete executable SOP. A model must state unresolved slots rather than invent laboratory settings. A fully specified step score is only justified where independent evidence actually supports those settings. Existing templates are agent-curated and not human-validated. PubChem AID ↔ ChEMBL document/paper mappings have not been comprehensively checked: cross-database duplication remains an audit task. For this reason, full template text and example protocols are not supplied; adding them requires a source audit first.

## Running a pilot

Give a model **only** `cases/case-N.input.json`, with a fixed instruction to satisfy its output contract using only that packet. Disable web access, raw-KB access and lookup of the held-out sources. Log the model/version, prompt, packet SHA-256, settings and complete output. Use the same instruction and inference settings across cases. Repeat runs if estimating variability; twenty purposively selected cases still cannot support general performance claims.

The explorer is a human audit site. Both `cases.js` and the graph tab expose the answers in source/data even when toggles are closed. **The toggle is visual concealment, not access control.** Never point an evaluated agent at this page or give it reviewer files. Serving files separately does not secure them; isolation must be enforced by the evaluation harness. No such harness is added here. Memorization cannot be excluded by removing retrieval evidence.

## Three-axis rubric

Report separate scores, explanations, citations, missing evidence and critical failures; do not average a wrong endpoint into a passing result.

| Axis | 0 | 1 | 2 |
|---|---|---|---|
| Suitability | Wrong endpoint/system or invalid causal claim | Plausible assay with incomplete question coverage | Directly answers the requested endpoint/system and states its limits |
| Procedural soundness | Essential stages absent, incompatible steps or invalid order | Coherent outline but unresolved conditions/controls | Supported ordered procedure, appropriate controls and parameter bindings |
| Numerical soundness | Invalid arithmetic, units or incompatible settings | Plausible design with incomplete support | Internally consistent, evidence-justified settings with uncertainty handled |

Examples of critical failures: purified kinase assay as the sole answer to case 3; treating viability as proof of BTK-specific causality; unsupported claim of the withheld potency as a retrieved fact; invalid concentration-series arithmetic. Reviewer judgments on sufficiency and compatibility need domain calibration. Missing reference information is marked **not assessable**, not silently wrong. Unsupported model certainty can still be penalized.

### Coverage diagnostic (separate from the rubric)

For a proposal with top concentration `T` in µM, dilution factor `f > 1`, and integer `n >= 2`, compute `c_i = 1000*T / f**i` nM for `i = 0..n-1`. Report the minimum/maximum, number strictly below/above the reference IC50, and log10 span `log10(max/min)`. Verify positive finite T and positive integer replicates.

Report whether the IC50 lies in the series and whether at least two points fall on each side; the latter is a **pilot design diagnostic**, not a universal biological requirement. Do not reward span alone or rank solely by narrowness. Review span, spacing, assay feasibility and uncertainty together. No numeric score weighting or optimal-width cutoff is validated yet.

Coverage is interpretable only for sufficiently comparable systems/assays. If a proposal changes assay format, ATP conditions, exposure or cell system and comparability is unknown, report the numerical coverage as descriptive only and mark scientific comparison not assessable. The CSVs do not supply a full ground truth for incubation times, volumes, controls or optimal concentration limits. A held-out IC50 is not a unique correct design or proof that a proposed assay will work.

## Baselines and audit checklist

Compare fixed-context LLM assembly with a deterministic, predeclared template-selection/parameter rule using the **same input**. Never tune baseline rules to the withheld measurements. Separately compare today's agent on its supported output fields; mark procedural generation N/A rather than fabricating it.

Before a scored run, a reviewer must confirm source mappings, remove duplicate evidence, approve the abstractions and rubric, check retained example compatibility, and decide whether each numerical comparison is assessable. Validate the grader on human-scored proposals including wrong endpoints, reversed detection order, invalid dilution parameters and honest abstentions. Dataset generation itself makes no model calls; expanded-run outputs and diagnostic results are recorded separately. No validated scientific rubric scores are claimed.
