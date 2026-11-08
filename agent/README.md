# agent/: aim 1, propose the missing experiment

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

Given a `Question` the knowledge base cannot answer ("does compound X inhibit target Y?"), decide whether the KB
already answers it, and if not, propose the experiment that would: an `ExperimentProposal` grounded in both graphs,
citing the nodes it used.

- **Reads:** `benchmark/questions.jsonl` (`Question`), `kg/*/graph/{nodes,edges}.csv`. Never `ground_truth.jsonl`.
- **Writes:** `out/<run>.jsonl`, one `ExperimentProposal` per question (`wwtn/schema.py`).
- **Flow:** resolve compound and target in the biology KG → get the target class → retrieve a protocol template by
  target class and assay format → the LLM fills the parameters (concentration range from similar compounds'
  potencies) and cites node IDs.
- **Baselines** (same model, for a fair comparison): bare LLM · LLM + literature search · LLM + both graphs.
- **Run:** `python -m agent.propose --questions benchmark/questions.jsonl --out agent/out/kg.jsonl`, or one
  question: `python -m agent.propose --question "Does CHEMBL5593141 inhibit the BTK kinase, and how potently?"`
  (`--question` with no text runs that demo question; `python -m agent.tools` prints every tool on it).
  `--runs-js demo/runs` also writes the trace for the demo page; `--model` picks the LLM.
- **Live demo:** `python -m agent.server` serves the deck and the demo page with the agent behind it (see
  `demo/README.md`).
- **How it works:** `tools.py` puts the two graphs behind four functions the model can call (`bio_kg_resolve`,
  `bio_kg_analogs`, `bio_kg_similar`, `protocol_kg_templates`); `anchor.py` turns the analogs plus the
  template's series shape into the recommended top concentration, deterministically; `propose.py` is a
  tool-calling loop on `wwtn.llm.chat_raw` that ends when the model calls `propose_experiment`; `trace.py`
  records every call, the anchor, the model's reasoning between calls and the proposal, which is what the demo
  page plays. Until `kg/*/graph/` exist, the tools fall back to the hand-written sample in `data/sample_kg/`
  (TODO(final) there) through the same code path.

## The tools on top of `kg/query.py`

`kg_backend.py` holds the graph side: one `kg.query.KG` for both graphs (`KG.load`, once per process), plus what
the seed graphs do not carry yet. `tools.py` shapes its results for the model and the demo page.

| tool | what it does | `kg/query.py` |
| --- | --- | --- |
| `bio_kg_resolve(compound, target)` | both nodes, plus the target's **whole class chain**, most specific first, and which of those classes actually carry templates | `KG.resolve`, `KG.classes` |
| `bio_kg_analogs(compound, target, k)` | the k compounds most similar to this one **with an IC50 on the same target** (RDKit Morgan r=2, 2048 bits, Tanimoto; repeated measurements as a median), with the target-wide potency spread as context and an `analogs` list carrying each analog's node ID (what `anchor.py` and the grader need) | `KG.activities`, `KG.potency_summary` |
| `bio_kg_similar(compound, k)` | the k compounds most similar to this one **anywhere in the graph**, with what each has been measured on (target, median IC50, n): the way in when the target itself is thin, or to borrow a well-studied relative's assay | `KG.nodes_df`, `KG.neighbors` over `INHIBITS` |
| `protocol_kg_templates(question_type, target_class="", target="")` | the templates applicable to the target (or a class) **or to any class above it**, filtered by the question type their `ANSWERS` edges name | `KG.neighbors` over `APPLICABLE_TO`, `KG.classes` |

Three things the seed graphs leave to the agent, each a `TODO(final)` where it lives:

- **The class chain.** A real target is `MEMBER_OF` its most specific ChEMBL class (BTK -> `chembl_class:143`,
  Tec family) while the seed templates are `APPLICABLE_TO` `chembl_class:1100` (Protein Kinase), so a template
  lookup has to walk `SUBCLASS_OF` upwards. `bio_kg_resolve` shows the chain so the model can see where it ends.
- **Question types.** The seed protocols route with `ANSWERS` edges to `qtype:...` nodes (the sample KG with a
  `question_type` prop); both are read the same way and normalised (`cellular_activity` -> `cellular_potency`).
  A question type nothing answers returns **no** templates and says which types the applicable ones do answer.
- **Similarity.** There are no `SIMILAR_TO` edges, so `bio_kg_analogs` computes Tanimoto on Morgan fingerprints
  between the query compound's `smiles` and those of the compounds measured on that target, caching the
  fingerprints per load. A query compound with no usable structure falls back to the target's most potent
  compounds and the overall spread, and says so rather than implying a similarity it does not have.

## The concentration anchor (`anchor.py`)

The template gives the *shape* of the series (spacing, point count, controls), generic across compounds; the
biology graph gives the *scale* for this one (its analogs' measured IC50s). Where to put the top concentration
is the join, and it used to be done in prose by the model — the one number that decides whether the experiment
works, with no provenance and no check. `anchor.py` does it deterministically and records the derivation:

```python
analogs = kb.bio_kg_analogs("CHEMBL5593141", "BTK", k=3)        # 0.72-19 nM, median 8.2 nM
shape = Shape.from_template(kb.protocol_kg_templates("potency", target="BTK")["templates"][0])
anchor = anchor_from_result(analogs, shape)                     # top 0.638 µM, not the template's 12 µM
anchor.to_dict()        # analogs used, statistic, multiplier + basis, bounds, series, confidence flag
```

- **The multiplier is derived, not asserted.** `top = median_analog_IC50 * f ** ((n - 1) / 2)` with the
  template's own spacing `f` and point count `n`, so half the points sit above the expected potency and half
  below — the sentence `rule:agm/anchor_series_on_analogs` and `rule:agm/bracket_expected_ic50` both quote
  (NBK92007). That is 78x for the kinase template's 9-point 2.97-fold series, 140x for a 10-point 3-fold one,
  the same order as the usual "100x the expected IC50" rule of thumb. **The AGM chapters cited in
  `kg/protocols/rules.yaml` state no numeric multiplier**, so the fallback used when no template shape is in
  hand (100x) is a flagged heuristic with a `TODO(final)` and carries no AGM citation.
- **Unweighted median**, on purpose: analogs arrive k=3 within a narrow Tanimoto band (0.578-0.597 for the demo
  compound), a weighted median over two or three points is a step function of the weights, and
  similarity-to-potency is calibrated nowhere in this repo. The similarities are recorded, so a later version
  can weight and show the difference.
- **Edge cases, each with an outcome** rather than a silent guess: **no usable analog** → `applicable: False`,
  so the agent falls back to the template default *and says it did*; **one analog** → fires, `confidence: low`,
  flag `single_analog`; **spread over 3 orders of magnitude** → fires, flag `wide_spread`; analogs the graph
  reports as censored (`>128`) or valueless → skipped, counted in `skipped` with the reason; analogs that are
  not structural analogs at all (the fallback for a compound with no usable structure) → flag
  `not_ranked_by_similarity`.
- **A default, not a constraint.** The `SYSTEM` prompt hands the anchor to the model and requires it to state
  `anchor_top_uM` and `anchor_analogs`; departing is allowed with `anchor_departure_reason`. `trace.py` records
  the anchor and whether the model followed or departed (`anchor.followed`, `anchor.departure_reason`) — a wrong
  anchor must not be systematised, so a departure is recorded, never corrected.
- **`check_series_consistent_with_analogs(experiment, analogs, ...)`** → pass/fail plus a reason, for the grader
  that does not exist yet (`benchmark/`). It catches both directions: a series whose top is more than one
  dilution step off the anchor, or that does not even span the analogs' median potency (*ignored the retrieved
  analogs*), and a proposal naming analog node IDs `bio_kg_analogs` never returned (*cited analogs it did not
  use*). It takes an `Experiment`, an `ExperimentProposal` or a plain dict, and recomputes the anchor with the
  **experiment's own** spacing, so a model that chose a different shape is judged on the shape it chose.

`compounds.py` resolves a compound the graph does not hold: name or ChEMBL ID in, structure out, trying the
graph, then the local ChEMBL SQLite dump (`kg/biology/chembl_db.py`, or `CHEMBL_SQLITE`), then the ChEMBL REST
API cached under `data/raw/chembl_compounds/`. It asks for **structure fields only** (`molecule_chembl_id`,
`pref_name`, `canonical_smiles`): the live ChEMBL release still holds the IC50s the benchmark hides, so reading
activities there would leak the answer. With that SMILES, `bio_kg_analogs` ranks analogs for a compound that is
not a node at all, and says in its summary that the structure came from outside the graph. No dump, no network
(`WWTN_OFFLINE=1`) or an unknown compound degrades to "unresolved" with a note, never an exception.

`kb.lookup()` (stage 1, before the model is called) distinguishes the two ways of not knowing in a `kind` field,
which the benchmark's abstain metric needs apart: `no_measurement` (both sides resolved; the pair is genuinely
unmeasured) and `unresolved` (the KB does not know the compound or the target), plus `answered`. `verdict` keeps
its old values and nothing is renamed, so the trace contract in `demo/README.md` holds.

## The demo question

`DEMO_COMPOUND`/`DEMO_TARGET`/`DEMO_QUESTION` in `tools.py`: **CHEMBL5593141 x BTK** (`Q06187`), "Does
CHEMBL5593141 inhibit the BTK kinase, and how potently?". It is answerable by experiment on the seed graph:
CHEMBL5593141 is one of the structure-only candidates in `kg/biology/seed/compounds.csv` (no IC50 edge anywhere
in the graph), BTK is one of the 19 seed kinases, and the candidate's nearest compounds measured on BTK are
BTK inhibitors at Tanimoto 0.53-0.60 (ibrutinib among them) with IC50s of 0.72-55 nM, against a target-wide
spread of n=1936, median 20 nM. `TODO(final): confirm with Seh Na's candidate list.` The previous example,
imatinib x KIT, is not in the seed graph at all (KIT is not one of the 19 targets); it lives on only in the
recorded traces in `demo/runs/`, which cannot be re-recorded without an API key.

## Tests

`python -m pytest -q agent` (or `kg agent`): `agent/tests/` builds a tiny KG in the `kg/README.md` format
(`conftest.py`) and covers the class-chain lookup, question-type routing including a type nothing answers,
similarity ranking, a structure-only and a structure-less query compound, the sample-KG fallback and the
tool-result shape the trace depends on; `test_propose_stub.py` drives `propose.py` with a stubbed LLM client
(no API key, no network). `test_anchor.py` covers the anchor's arithmetic, every edge case, the binding to
`rule:agm/anchor_series_on_analogs` (so the rule and the function cannot drift) and the consistency check in
both failure directions; `test_anchor_trace.py` the trace fields and follow/depart in the loop;
`test_anchor_seed_graph.py` the worked example on the real seed graph. The checks against the real
`kg/*/graph` skip themselves when those are missing.
- LLM calls go through `wwtn.llm` (`chat_raw` for tool calling); the model ID is recorded in each proposal.
- Baselines (bare LLM, LLM + literature search) are not written yet. <!-- TODO(final): baselines -->
