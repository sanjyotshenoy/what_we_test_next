# Discussion log

Concise record of what the team discussed and decided (mostly in Discord), newest last. One entry per topic:
**decided** / **suggested** (proposed, not yet agreed) / **open**. Append as we go; keep each entry short and link
to the file it changed. Snapshot of the whole project: [HANDOFF.md](HANDOFF.md).

## 2026-11-07

**The idea** (meeting). When a literature agent (PaperQA-style) says "I don't know", propose the experiment that
would answer it, grounded in KGs, then run it on the OT-2. Aim 1 = propose, aim 2 = execute. First domain:
"does compound X inhibit target Y?" → IC50 dose-response by serial dilution.
- Decided: verifiable setup by holding facts out of the KB; the OT-2 run is a demo (food colouring), the
  simulator is the evaluation.

**Repo structure** → [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), `wwtn/schema.py`.
- Decided: one folder per workstream; folders exchange JSONL/CSV in fixed formats; `TODO(final)` tags anything
  mock ([TODO.md](TODO.md)).

**Two benchmarks + models** → `slides/.../benchmarks.js`, `wwtn/llm.py`.
- Decided: B1 = is the proposed experiment right (bare / + literature / + KGs); B2 = does the OT-2 protocol run.
  Models (Nebius): DeepSeek-V4-Pro-0813, Kimi-K3, Qwen3.8-27B, GLM-5.3 (GLM replaced gpt-oss on request).
- Open: confirm the four are live on our key.

**Modality vs parameters** (Seh Na's write-up).
- Suggested: the assay type follows from the question's form (rule layer); the KG matters for *parameters*
  (analog IC50s set the concentration range); sparse analogs → widen to a two-stage screen.
- Risks: with IC50-only questions modality is constant (ties across arms); hold out by ChEMBL *document* (same-paper
  analogs leak the answer); the range metric must penalize width.

**Robot side.**
- Suggested: agent writes a hardware-agnostic procedure, a backend compiles it; lab inventory file (`lab.yaml`);
  audit final per-well concentrations (the simulator passes wrong biology); human approves before the robot moves.
- Opentrons API for the OT-2-only case (official simulator, more LLM training data); PyLabRobot if OT-2 and plate
  reader are both driven from one script.
- Done: Emmy's reference MIC protocol in [Opentrons/](Opentrons/).

**Retrieval design.**
- Suggested: no GraphRAG library; seed index (names/IDs → nodes) + typed tools (`resolve`, `neighbors`,
  `analogs`, `templates`) returning small tables with citable IDs; node text cards from templates (not an LLM),
  embedded with Qwen3-Embedding-8B; build them after removing held-out facts.
- Open: does each Nebius model support function calling (else a JSON action loop)?

**Protocol "KG" and KB expansion.**
- Decided: the only real graph for now is the biology KG; protocols are a structured table keyed by (question
  type, target class), assay-level ("what"), not robot steps; promote to a graph when adding experiment instances.
- Suggested: KB has a read path (seed index + tools) and a write path (ingest, our results, extracted facts), each
  with provenance; writes go to overlay files so benchmark snapshots stay fixed.
- Suggested: continual-update demo v0 (curated) → v1 (+ the held-out paper as the "new paper") → v2 (+ our
  measured IC50); show the effect by re-asking. Evidence rows in ChEMBL activity shape + summary edges in the
  base KG's (Biolink) format, re-derived from evidence; conflicts kept, not overwritten.

**Data sources and schema.**
- Suggested: ChEMBL (activities, assays, docs/year: facts + ground truth), PubChem BioAssay (protocol text),
  NCATS Assay Guidance Manual (10–20 design rules), Opentrons tutorial (code skeleton). Scope: kinases, IC50 '='
  in nM, confidence ≥ 8, time split by `docs.year`. Tables: `activity`, `assay`, `template`, `rule`.
- Open: check real column names / licences before building.

**Benchmark grading.**
- Agreed: structure the ground truth (same schema as outputs); deterministic checks for deterministic fields,
  LLM judge only for fuzzy ones (it sees the whole experiment, grades only its fields, quotes the paper text).
- Agreed: score **fidelity** (matches the paper) separately from **soundness** (would it answer the question);
  soundness rubric: right compound × target, readout measures the asked quantity, interpretable controls,
  feasible with our inventory (deterministic vs `lab.yaml`).
- Suggested: judge hygiene (blind, different model family, per-field judge–human agreement on ~10 labels);
  multiple acceptable references (best match); grade parameters conditional on the chosen design.
- Agreed direction: a **rubric tree** (design / parameters / controls / execution; precedent: PaperBench) covering
  both benchmarks; stretch: 2–3 orthogonal experiments scored by coverage.
- Open: branch weights and the range metric, fixed before writing the grader (`benchmark/rubric.yaml`).

**Is it a new benchmark?** (literature search).
- Nothing found covering the whole chain. Closest: Gamow Labs LabBench (withheld next step, no execution),
  SCOPE 2608.03501 (ML, hidden experiments), Text2WetLab (protocol → OT-2 code, experiment given), BioLab bench
  2606.31763, SciPredict 2604.10718 (motivates abstention).
- Defensible claim: first benchmark scoring held-out bioassay questions end to end: abstain → KG-cited,
  parameterized assay design → simulator-checked OT-2 execution, fidelity vs soundness, calibrated judges.
  Don't claim "first" for experiment design, time splits, rubric trees, LLM→OT-2 or abstention alone.
- Scope it as a spec + pilot (5–10 questions, one target class, 4 models).

**Seed KG + query layer** (zetamac, branch `benchmark-v0`, not pushed yet as of 18:00).
- Built: ChEMBL client, candidate-paper script, seed biology graph (`kg/biology/build_seed.py`: targets of kept
  candidates, their pre-2024 IC50s with compound/assay/paper, ChEMBL protein-class chain; candidate compounds
  structure-only), seed protocol graph (`kg/protocols/seed.py`: 3 kinase templates, potency / cellular / binding,
  default 10 µM, 3-fold, 10 points, 3 replicates), `kg/query.py` (`resolve`, `neighbors`, `classes`,
  `activities`, `potency_summary`, `templates`; offline, IDs on every result), `benchmark/check.py` (cutoff,
  no answer edge, coverage, integrity).
- Suggested: warn on same-series leakage (pre-2024 near-identical analogs on the same target); weight the potency
  prior by structural similarity in `agent/` (target-wide summary is coarse); report the template defaults as
  their own B1 arm; prefer the newest candidates (models have likely seen 2024–25 papers).

**Scalability with NVIDIA RAPIDS** (ramiiith, after Ben Busby's talk).
- Suggested: write the KG and query layer against plain NetworkX + pandas so GPU backends are a switch, not a port:
  nx-cugraph (NetworkX backend dispatch, `NX_CUGRAPH_AUTOCONFIG=True`), `python -m cudf.pandas` (ChEMBL activity
  tables), cuVS for a large embedding index. A GPU is available (RTX 5090, 32 GB, on the bot's machine).
- At pilot scale the GPU won't show; the slide is "same code on full ChEMBL / OptimusKG, CPU vs GPU timings".
- Open: does `kg/query.py` use NetworkX/pandas?

**`kg-scaffolding` branch** (zetamac, 18:40; reviewed).
- Built: `kg/backend.py` (one codebase, `WWTN_GPU=1` switches to cudf.pandas + nx-cugraph, refuses if pandas or
  networkx were imported first), `kg/graph_io.py`, `kg/query.py` (pandas frames + networkx MultiDiGraph),
  `kg/biology/build_seed.py` + `chembl_db.py` (local ChEMBL 37 SQLite dump, IC50 '=' nM before 2024, `LeakageError`
  on post-cutoff or undated rows), `kg/protocols/seed.py` (3 templates). 43 tests pass, 1 GPU test skipped (no RAPIDS
  on the review machine). Biology graph not built yet (needs the ~30 GB dump).
- Suggested: store or filter `assays.confidence_score` (cell-based / low-confidence assignments become INHIBITS
  edges); dedupe node IDs across graphs in `KG.__init__`; same-series leakage warning in `benchmark/check.py`.
- Open: PR / merge into main; GPU timings on the RTX 5090 once a full-size graph exists.

**Compute and a public demo** (ramiiith, 18:50).
- Brev credits: the team's one-time promo code is on ramiiith's account; share access by org invite / SSH keys,
  never by posting credentials. The RTX 5090 on the bot's machine covers the GPU speedup demo.
- Brev tunnels give a shareable URL but go through Cloudflare authentication (first visit needs a browser login),
  so they may not be fully public; no documented public IP / open ports.
- Suggested: keep the public demo static (already on Cloudflare Pages) replaying real traces; optional live mode = a
  small backend behind a Brev or Cloudflare tunnel, tested from outside the network, with recorded traces as fallback.

**The demo becomes a real app** (ramiiith / professorduckydoo, 18:58).
- Decided: the demo moved from `slides/talks/biohack/demo/` to [demo/](demo/) at the repo root, so work on it
  doesn't redeploy the slides. It is self-contained (fonts copied in); the deck reaches it through the symlink
  `slides/talks/biohack/demo -> ../../../demo`, which `build_site.sh` now follows (`cp -rL`). Publish demo-only
  changes by running the Deploy slides workflow by hand.
- Plan in [demo/README.md](demo/README.md): (1) the pipeline writes real traces in the existing format, (2) optional
  live backend that returns a trace, `find()` fetches it, (3) recorded traces stay as the fallback.

**Seed biology graph pushed** (zetamac, `kg-scaffolding` @ b175563, 19:17).
- 19 kinases (targets of the candidate papers), ChEMBL 37 before 2024: 15,359 nodes / 19,179 edges (17,719 IC50s),
  4.9 MB; filters checked on the real dump (keep "Manually validated", drop mutant assays); 22 candidate compounds
  structure-only. Curation notes in `kg/biology/README.md` (per-target counts, thin targets, 2,000-per-target cap).
- Leakage check (RDKit Morgan r2 Tanimoto vs all pre-2024 compounds with IC50s): no candidate has an IC50 edge; max
  similarity 0.29–0.67, none ≥ 0.7 (borderline CHEMBL6162604 0.67, CHEMBL6172406 0.62).
- Suggested for curation (Seh Na): prefer candidates with some moderately similar same-target analogs (where the KG
  can beat a guess); decide on thin targets (TLK2, LATS2, SIK1, SIK3) as drop vs a "sparse" stratum.
- Open: push the candidate-paper list / (compound, target) pairs (`benchmark-v0`); merge `kg-scaffolding` into main.

**What each source is for** (zetamac, 19:24).
- Agreed: NCATS Assay Guidance Manual → generalizable template rules (also grader checks for soundness); PubChem
  BioAssay → specific written protocols; Opentrons tutorial in context for OT-2 code generation.
- Suggested: PubChem protocols as template sources / step-tree examples, or an extra question set from PubChem
  confirmatory AIDs time-split by deposition date (richer step-level ground truth than paper methods). For OT-2
  generation, use Emmy's reference protocol (`Opentrons/`) as the few-shot example, pin the API level (2.28) in the
  in-context docs, pass labware `load_name`s from `lab.yaml`, and feed back simulator errors (≤ 3 fixes).

**PR #1: live agent + demo figures** (ramiiith / allgofine, 19:28).
- `agent/propose.py` + `agent/tools.py` (tool-calling loop over the KGs, traced), `agent/server.py` (FastAPI: runs
  the agent live and streams the trace to the page), demo stepping, model switch, theme button, two figures. Agent
  still uses hand-written sample graphs (`agent/data/sample_kg`).
- Merged with main's demo move on branch `pr1-merged` (demo files into `demo/`; server mounts `demo/` itself since
  StaticFiles won't follow the symlink). Open: fast-forward main to it.

**Populating the experiment DB** (zetamac, 19:31).
- Decided: decouple OT-2 code generation for now; focus on the database.
- Suggested: a template = one generalizable experiment type (purpose and when to use it from the Assay Guidance
  Manual; abstract step tree, parameter ranges and exemplar AIDs from PubChem confirmatory assays; AGM rules as a
  `rule` table). Populate by LLM extraction of ~5–20 AIDs per archetype, aligned and hand-checked. Grading trees take
  the skeleton from templates but values from the held-out paper / AID (not circular). AGM rules → deterministic
  soundness checks.

**Demo platform split: ouroboros** (Sanjyot / professorduckydoo / ramiiith, 19:40).
- Decided: the full demo platform lives in its own private repo, `sanjyotshenoy/ouroboros`, and pulls from this
  research repo (one-way). This repo keeps `demo/` as the offline fallback; the bot gets read-only access via a
  deploy key. Interfaces ouroboros depends on (the trace format in `demo/README.md`, `wwtn/`, `agent/`) change only
  with a note here.
- Suggested (not decided): no git submodule (it would break the slides deploy and force ouroboros access on every
  clone); the deck's demo slide can point at ouroboros' deployed URL once there is one.
- Done (19:45): `pr1-merged` merged into main as PR #2 (`d80ade2`); live deck redeployed with the agent's real trace.

**Benchmark data plan** (zetamac, 19:51).
- Decided: a simple KG on relatively well-studied kinases (ChEMBL subgraph, `kg-scaffolding`), handed to Seh Na to
  validate and polish; candidate papers and benchmark edges come from her. Protocol templates from NCATS AGM +
  PubChem BioAssay (hierarchical trees); with templates in context, an LLM extracts each held-out paper's protocol
  as the ground truth the judge grades against.
- Suggested guardrails: the template gives structure, the paper gives values (extractor leaves fields empty when the
  paper is silent; quote a span per field); hand spot-check extracted ground truth; extract with a model that is not
  among those evaluated (and judge with another).
