# What we test next — project handoff (as of 2026-11-07, ~12:00 ET)

Standalone briefing for a coding agent (or a person) picking this project up from scratch. It records what the
project is, every decision made so far and why, what exists in the repo, what does **not** exist yet, and what to
do next. Written by the team's Discord assistant (Claude) from the team's Discord discussions, two meeting
transcripts shared in Discord, and the repo itself. Where something is a suggestion rather than a decision, it
says so.

> **Status in one line:** the *plan, data contracts, slides and a mock demo* are done; **none of the pipeline code
> (knowledge graphs, agent, robot-protocol generation, benchmark) has been written yet.**

---

## 1. The event and the team

- **Event:** Nucleate Pittsburgh BioHack 2026, **Biotech Track: Problem #2**.
- **Team name:** "Team Zhang et al."
- **Members** (as on the title slide): Aidan Zhang, Emmy Nguyen, Jimmy Hsu, Ramith Hettiarachchi, Sanjyot Shenoy,
  Seh Na Mellick, Xiaochen Zhai.
- **Talk title:** *Closing the Loop Between Knowledge and Discovery*.
- **Hardware available:** an Opentrons **OT-2** liquid handler (connected to a laptop; SSH / USB-IP forwarding
  was discussed for remote access) and a **plate reader**. Both reportedly also controllable via PyLabRobot.
- **Compute/LLMs:** credits on **Nebius Token Factory** (OpenAI-compatible API). The API key is *not* in the repo
  and must never be committed or pasted in chat.

Work split, as far as the (speech-to-text, partly garbled) meeting transcript shows — tentative, and the folder
READMEs still say "Owner: (fill in)": Seh Na — problem statement / a verifiable system; Sanjyot — biology knowledge
graph; Jimmy — agents that write lab protocols (OT-2 side); Emmy — a hand-written ground-truth OT-2 protocol;
someone (unclear who) — experiment/protocol knowledge graph; someone (unclear who) — evaluation/benchmark;
Ramith — repo, slides, orchestration. **Confirm with the team.**

---

## 2. The idea (the claim)

Literature agents (e.g. FutureHouse/Edison **PaperQA**, the "Has Anyone?" site) can answer a question when someone
has already done the experiment. **When the honest answer is "I don't know", nothing tells you what to do next.**
We build that next step:

1. **Aim 1 — propose:** given a question the knowledge base can't answer, propose the experiment that would answer
   it, **grounded** in two knowledge graphs (biology + experimental protocols), **citing** the graph nodes it used.
2. **Aim 2 — execute:** turn the proposal into a protocol a lab robot runs (Opentrons OT-2), check it in the
   simulator, and (for the demo) run it on the real robot.
3. **Close the loop** (the pitch): the measured result is written back into the knowledge graph, so the next
   question starts from more knowledge.

**First domain:** "Does compound X inhibit target Y, and how potently?" → an **IC50 dose-response** via a **serial
dilution**. Chosen because it is narrow, verifiable, and maps directly onto a serial-dilution OT-2 protocol.

**Not doing:** GNNs, open-ended hypothesis generation, phenotype–genotype questions, inventing new assay methods.

---

## 3. Key design decisions (and why)

### 3.1 How the benchmark questions are made: holding facts out
Take real drug–target IC50 results (from **ChEMBL**), **delete those facts from our knowledge graph**, then ask
"does X inhibit Y?". The KB genuinely can't answer; ChEMBL's assay record is the ground truth. Every question is
unknown to the system but verifiable by us.
- **Leakage to avoid:** ChEMBL analogs often come from the *same paper* (a congeneric series in the same assay),
  which would hand the analog prior the answer — **hold out whole ChEMBL documents**, not just the one edge. Also
  build any node text/embeddings *after* removing held-out facts.
- **Contamination:** the LLM may have memorized the IC50. We score the *proposed experiment*, not the answer, and we
  check it **abstains** ("the KB can't answer") rather than quoting a memorized number.
- Say "held-out questions", not "link prediction", in slides.

### 3.2 The two knowledge graphs
- **Biology KG:** compounds, targets, target classes, known activities (IC50s), similar compounds. Use an existing
  graph rather than building one: **ChEMBL** (activities, assays, targets), **UniProt**, **OptimusKG** (Zitnik lab,
  arXiv 2604.27269; ~190k nodes, 21.8M edges from 65 databases, Parquet on Harvard Dataverse + PyPI) or PrimeKG.
- **Experiment/protocol KG = the "what", not the robot:** assay-design knowledge — which assay types fit which
  target class (biochemical vs cell-based), readout, typical concentration ranges, controls, replicates —
  **BAO-tagged**. It does *not* need to know about Opentrons; robot code is a separate step. (Team agreed on this
  split.) Suggested additions: an `ANSWERS → QuestionType` edge (potency, binding, fitness…) plus a plaintext
  `purpose` per protocol; and **experiment instances** ("assay X ran protocol P on target T with compound C →
  result R", from ChEMBL assays) as the "knowledge gained" edges that let retrieval find precedent.
- **The bridge between graphs is `TargetClass`:** `Target -MEMBER_OF-> TargetClass` and
  `Protocol -APPLICABLE_TO-> TargetClass`.

### 3.3 Retrieval: tools over small typed graphs, not a GraphRAG library (suggestion, not yet adopted)
Graphs are small and typed and the questions structured, so **LLM tool calling over explicit query functions** is
recommended over GraphRAG/LightRAG (built for big unstructured corpora; add indexing cost; blur citations):
- **Seed index** (entity resolution): name/synonym → node ID; exact/fuzzy first, embeddings for the fuzzy rest.
- **Typed tools from the seeds**, each returning a compact **table with node IDs** (never raw subgraphs):
  `resolve(name)`, `neighbors(id, rel)`, `analogs(compound, target, k)`, `templates(question_type, target_class)`,
  maybe `path(a, b)`.
- **Context to the LLM:** question + tool tables + the `ExperimentProposal` schema; it may cite only IDs that appear
  in tool results (makes citations checkable).
- **Node text for embeddings:** generate per-node "cards" from a **template** (type, name, key props, 1-hop
  relations), not with an LLM; embed with `Qwen/Qwen3-Embedding-8B` on Nebius (cheap) into numpy/FAISS.
- **Protocol lookup:** exact by (question type, target class, BAO format) first; embeddings only if templates get
  numerous. LLM-extraction of protocols enriches templates but is not the critical path.
- **Function calling on Nebius:** not verified for every model; fall back to a JSON "action" (ReAct-style) loop.

### 3.4 Modality vs parameters (from Seh Na's write-up — the strongest idea so far)
- **Modality** (which assay) is set by the *question's form* (potency → dose-response; fitness → competition
  assay; binding → e.g. thermal shift), plus entity type and lab capabilities — **not** by how well studied the
  target is. Route it with a small rule layer.
- **Parameters** (top concentration, dilution factor, number of points, replicates) need priors from **similar
  compounds** — that's where the graph matters and where sparsity hurts. Analog prior = similarity-weighted IC50s
  (Tanimoto on fingerprints via RDKit + graph distance) → gives centre *and* spread of the range.
- When analogs are sparse: **widen** (a broad log-scale screen, then a focused series) rather than abstain.
- **Caveat:** with IC50-only questions, modality is always "dose-response", so modality columns will tie across
  arms; either accept that or add a second question type.
- **Density bias:** report coverage (how many supporting neighbours), stratify results by node degree (expect
  flat for modality, falling for range accuracy). Heavier fixes (degree-matched null / XSwap, node2vec) are optional.
- **Don't grade with the graph you generated from** (circular); anchor grading to ChEMBL / paper methods.

### 3.5 Robot side
- **Two layers:** the agent writes a **hardware-agnostic procedure** (JSON steps: transfer/dilute/mix/incubate/
  read, with volumes, concentrations, wells + a readable version), then a **backend** compiles it to robot code.
- **Opentrons Python API v2** for the OT-2 (official headless simulator `opentrons_simulate`; much more public code
  so LLMs write it better). **But** if both OT-2 and plate reader are driven through **PyLabRobot**, PLR is better
  for the *real run* because one script drives both instruments; it also has simulation backends. Keep PLR as the
  "any robot" story / second backend; verify its OT-2 details at docs.pylabrobot.org.
- **Lab inventory file** (`execution/lab.yaml`, suggested): pipettes, tip racks, plates, reservoirs, deck slots,
  reagent stock concentrations, plate-reader modes. The agent may use only what's listed.
- **Plate design step** (proposal → well map, volumes keeping DMSO % constant, timeline) as a checkable JSON
  artifact, separate from code.
- **Checks:** simulator must run to completion; **audit** that recomputes final per-well concentrations from the
  executed commands and diffs against the plan (the simulator alone passes wrong biology); volume ≤ pipette max,
  ≤ 96 wells, enough tips. Agent loop: look up API docs → simulate → fix, up to N rounds. **Human approves** plate
  map + deck before the real robot moves; never auto-retry liquid handling after an error.
- The OT-2 has no gripper: moving the plate to the reader is a human step (explicit pause in the script).
- **Demo run:** food colouring into water; absorbance vs concentration should be a clean line.
- Prior work to cite: Inagaki et al. arXiv 2304.10267 (GPT-4 writes OT-2 code; success = runs in simulator);
  PRISM arXiv 2601.05356 (plan/critique/validate + digital twin). Official skeleton:
  docs.opentrons.com/v2/tutorial.html (serial dilution).

### 3.6 The two benchmarks (slides already show them as empty templates)
**Benchmark 1 — is the proposed experiment right?** Same questions, same prompt, three arms per model:
**bare LLM → + literature search → + both KGs** (the KG lift is the headline). Field-by-field grading against the
held-out ChEMBL assay: abstains (doesn't quote a memorized IC50) · assay + readout · **range hits the IC50** (true
IC50 inside the series, ≥ 2 points each side) · series/controls/replicates · valid citations (reported in text —
near 100% by construction if citations come from retrieval; better: are the parameters *consistent* with the cited
analogs). LLM judge only for free-text rationale. **The range metric must penalize width** (e.g. hit − λ·log-span,
or hits per well) or "widen" always wins — **decide before writing the grader.**

**Benchmark 2 — does the OT-2 protocol run?** Every model writes OT-2 code for the *same ground-truth experiments*
(so code is scored apart from benchmark 1): runs in simulator first try · runs within ≤ 3 error-feedback fixes ·
**final per-well concentrations match the hand-written reference protocol** · volumes/tips/deck valid · end to end
(from the model's own benchmark-1 proposal) · cost per protocol. A fixed template filled with the proposal's numbers
is the **baseline**; free agent generation is the method.

**Models compared (Nebius Token Factory IDs):**
`deepseek-ai/DeepSeek-V4-Pro-0813`, `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-27B`, `zai-org/GLM-5.3`.
(gpt-oss-120b was dropped from the benchmark at the team's request; it stays the cheap default for dev calls.)
Nebius retires models often — **9 Nov 2026** removes GLM-5.1, Kimi-K2.6/K2.7-Code, DeepSeek-V4-Pro (non-0813),
Qwen3.5-397B and others. **Confirm the four are live on the team key** with `python -m wwtn.llm --models`.

---

## 4. The repository

- **GitHub:** `https://github.com/ramithuh/what_we_test_next` (private; ask Ramith to be added as a collaborator).
  Clone: `git clone git@github.com:ramithuh/what_we_test_next.git`.
- **Branch:** `main` only. 23 commits so far; latest `61b5df5` (2026-11-07 08:08 ET). Almost all scaffolding was
  done by the assistant; teammates have not pushed pipeline code yet.
- **Live slides** (unlisted Cloudflare Pages; share only within the team):
  `https://zhang-etal-biohack.pages.dev/075d295f820d3892ac1d1010c3ffdc8f31a597f041dc3d2d/talks/biohack/`
  — demo page at the same address + `demo/`.
- **Google Docs / other docs:** none known to the assistant. A team "document" with a big-picture framework was
  mentioned in a meeting, but it was never shared in Discord — ask the team.

### 4.1 Layout
```
README.md          project summary, layout, data flow, how to call LLMs, slides
CONTRIBUTING.md    team rules (stay in your folder, files as contracts, git, data, TODO(final))
AGENTS.md          rules for coding agents (CLAUDE.md just points here) — read it first
TODO.md            how to list unfinished/mock items + a checklist snapshot
requirements.txt   openai>=1.40, python-dotenv>=1.0, pydantic>=2.0
.env.example       NEBIUS_API_KEY=, NEBIUS_MODEL=openai/gpt-oss-120b   (copy to .env, git-ignored)
.gitignore         .env, __pycache__/, *.pyc, .venv/, data/raw/, out/
wwtn/llm.py        Nebius client: chat(), models(), CLI; DEFAULT_MODEL; EVAL_MODELS (the four)
wwtn/schema.py     pydantic data contracts + read_jsonl/write_jsonl
kg/README.md       the shared node/edge CSV format for both graphs
kg/biology/        README only            (biology KG)
kg/protocols/      README only            (protocol KG)
agent/             README only            (aim 1)
execution/         README only            (aim 2)
benchmark/         README only            (questions, ground truth, grading)
slides/            the live slide deck (template "protein-design-interactive-slides" by Ramith)
.github/workflows/deploy-slides.yml   deploys slides on push to main (needs CLOUDFLARE_API_TOKEN secret)
```

### 4.2 Conventions (from CONTRIBUTING.md / AGENTS.md)
- Each workstream owns its folder; changes to `wwtn/` (especially `schema.py`) or another team's folder need a
  heads-up. Folders talk through **files**, not each other's code: JSON Lines whose models are in
  `wwtn/schema.py`, and graph CSVs in the `kg/README.md` format. Start against 2–3 hand-written lines.
- Run code from the repo root as modules: `python -m agent.propose ...` (so `import wwtn` works). Python 3.10+.
- All LLM calls go through `wwtn.llm.chat` (switch models in one place). Never print/log/commit the API key.
- Commit small, `git pull --rebase` before pushing; pushing your own folder to main is fine.
- Small data (< ~10 MB) may be committed in your folder's `data/`; bigger goes in `data/raw/` (ignored) with a
  download script. Generated output in `out/` (ignored) unless others need it.
- **`TODO(final)`**: anything mock, placeholder or unconfirmed gets a `TODO(final): ...` comment where it lives;
  list them with `grep -rn "TODO(final)" --exclude-dir=.git .`.
- **Pushing anything under `slides/` redeploys the live deck.** Run the deck checker first (§4.6).

### 4.3 Data contracts (`wwtn/schema.py`)
Files: `benchmark/questions.jsonl` (Question) → `agent/out/<run>.jsonl` (ExperimentProposal) →
`execution/out/<run>/` (protocol `.py` per question + ExecutionResult lines); `benchmark/ground_truth.jsonl`
(GroundTruth; the agent must never read it); `benchmark/held_out.csv` ((compound, target) pairs kg/biology must
leave out).
- `Question`: id, text, compound (KG ID, e.g. ChEMBL), target (e.g. UniProt), split ("dev"|"test").
- `Experiment`: assay_type, readout, system, top_concentration_uM, dilution_factor, n_points, replicates (3),
  controls (list).
- `ExperimentProposal`: question_id, answerable_from_kb, answer (if answerable), experiment (if not), rationale,
  citations (KG node / protocol IDs), model.
- `GroundTruth`: question_id, experiment, source (e.g. "CHEMBL assay CHEMBL…").
- `ExecutionResult`: question_id, protocol_path, simulated_ok, error.
These fields were a first guess; benchmark/agent owners may change them early (tell the team).

### 4.4 Graph format (`kg/README.md`)
Each graph writes `graph/nodes.csv` (`id, type, name, props(JSON), source`) and `graph/edges.csv`
(`src, rel, dst, props(JSON), source`) into its folder (committed). Use source IDs (ChEMBL, UniProt, BAO); invent
`proto:...` IDs only for our own nodes. Keep provenance (`source`) on everything; normalize units in code (µM, µL,
min, °C); BAO IDs for assay types/readouts. Useful BAO terms: IC50 `BAO:0000190`, concentration-response
`BAO:0010258`, single-protein format `BAO:0000357`, cell-based `BAO:0000219`, fluorescence intensity
`BAO:0000363`, % inhibition `BAO:0000201`, positive/negative control `BAO:0000080`/`BAO:0000079`; replicates
`OBI:0500018`.

### 4.5 Calling LLMs
```bash
pip install -r requirements.txt
cp .env.example .env              # fill in NEBIUS_API_KEY (never commit it)
python -m wwtn.llm --models       # model IDs the key can use
python -m wwtn.llm "your prompt"
```
`from wwtn.llm import chat, EVAL_MODELS; chat("...", model=..., system=..., temperature=0.2)`.
Base URL `https://api.tokenfactory.nebius.com/v1/` (override with `NEBIUS_BASE_URL`). Tested only up to auth
(a fake key gets 401) — **no real completion has been run yet.** Repo secrets on GitHub are only visible to
Actions; to run locally, put the key in `.env`.

### 4.6 Slides (`slides/talks/biohack/`)
Live, code-drawn deck (HTML + manim-web, Reveal.js for navigation; no build, works offline from disk). Read
`slides/AGENTS.md` before editing. Each slide is a JS module in `slides/`; order = `<script>` tags in `index.html`.
Current slides:
1. **title** — title, subtitle, team photos (Aidan, Ramith, Sanjyot, Seh Na from the CMU CPCB students page; Emmy's and Xiaochen's their own; in
   `data/team/`; Jimmy shows initials until his photo arrives — add file
   `data/team/<first-last>.jpg` and the name to `PHOTOS` in `title.js`), "Team Zhang et al." large on the wave,
   "(Biotech Track: Problem #2)".
2. **outline** — 6 sections: Problem · Approach (2.1 biology KG, 2.2 experiment KG) · Evaluation · Results ·
   Live demo · Closing the loop with the lab (dummy; confirm).
3. **loop** (`loop.js`, 6 clicks) — the big-picture diagram: a scientist asks "Does imatinib inhibit KIT?" → "?"
   (the missing link); literature gives prior knowledge but no answer; cloud lab; "?" sends the next experiment;
   lab feedback returns; answer goes back to the scientist.
4–8. placeholder slides from `blank.js` (each says "Placeholder: …" on screen).
9–11. **benchmarks** (`benchmarks.js`): bar-chart templates, one bar per model, every bar "—" until filled:
   benchmark 1 overall (bare / +lit / +KGs, a click each), benchmark 1 by field, benchmark 2. Fill
   `RESULTS[chart][modelId][groupKey] = percent`. `MODELS` must match `EVAL_MODELS` in `wwtn/llm.py`.
12. Results placeholder.
13. **demo** (`demo.js`) — the demo page in a full-bleed iframe; this slide switches the deck to dark while shown.
14. Closing-the-loop placeholder.

Check before pushing (needs Playwright + Chromium once: `pip install playwright && playwright install chromium`):
```bash
cd slides && python tools/check_deck.py talks/biohack            # all slides, both themes; fails on console errors
python tools/check_deck.py talks/biohack --slide loop --back      # one slide, also stepping backwards
```
Look at the pictures in `talks/biohack/check/` (git-ignored). Present locally: `cd slides && python -m
http.server 8000` → `http://localhost:8000/talks/biohack/` (keys: →/← step, S notes, O overview, T theme, F full
screen). Deploy: automatic on push to main if the `CLOUDFLARE_API_TOKEN` repo secret is set (the link is kept via
the committed `slides/.pages-prefix`); by hand `slides/tools/deploy_unlisted.sh zhang-etal-biohack` (needs
`wrangler login`).

### 4.7 Demo page (`slides/talks/biohack/demo/`)
Static page: a search box with a predefined query and a **timeline of one query's lifecycle**: (1) ask the KB →
"I don't know" (record held out); (2) tool calls `bio_kg.resolve`, `bio_kg.analogs`, `protocol_kg.templates`;
(3) reasoning; (4) proposed experiment with citation chips; (5) procedure + 96-well plate map + OT-2 script +
simulator status; (6) check against the held-out paper. Paced for an audience (shimmering "working…" states,
"running…" tags on tool calls, streamed reasoning, reading pauses; ~80 s; *Next step* / *Show all*; `?all`,
`?run=<id>`, `?theme=dark`). Timing constants at the top of `demo.js`.
**It plays a MOCK trace** (`runs/kit_imatinib.js`, imatinib × KIT; IDs real, numbers illustrative, page shows a
"Mock trace" badge). The trace format is in `demo/README.md` and mirrors `wwtn/schema.py`; when the pipeline is
real, an exporter writes the same trace and the page shows the real run with no frontend change.

---

## 5. What's left (the `TODO(final)` list, 2026-11-07)
On screen:
- Replace the mock demo trace with a real run (`mock: false`, real held-out ChEMBL assay ID) — `demo/runs/`,
  `demo/index.html`, notes in `slides/demo.js`.
- Fill benchmark chart `RESULTS` — `slides/benchmarks.js`.
- Replace or delete the "Placeholder:" slides — `slides/blank.js`; confirm the outline — `slides/outline.js`.
- Photo for Jimmy Hsu — `slides/title.js`.
Behind the scenes:
- Confirm the four models are live on the key — `wwtn/llm.py`, `benchmarks.js`.
- Pick the range-accuracy metric (penalizing width) before writing the grader — `benchmark/README.md`.
- Fill in folder owners in each README.
And the actual pipeline, none of which exists yet (suggested order):
1. **benchmark/**: ~5 hand-picked held-out questions in one target class (kinases), ground truth from ChEMBL,
   `held_out.csv` (hold out by ChEMBL document).
2. **kg/biology/**: small subgraph (compounds, targets, target classes, IC50s, analogs) minus held-out facts →
   `graph/*.csv`.
3. **kg/protocols/**: 3–5 hand-written BAO-tagged dose-response templates (biochemical enzyme inhibition, cell
   viability, binding) → `graph/*.csv`; enrich later from ChEMBL assay descriptions / protocols.io (retrieval only:
   its terms forbid training on its content; API needs a token).
4. **agent/**: seed index + typed tools + Nebius call → `ExperimentProposal` lines; three arms (bare, +lit, +KGs).
5. **benchmark grader** (`python -m benchmark.grade`).
6. **execution/**: procedure JSON → OT-2 code (template baseline + agent loop) → `opentrons_simulate` + audit;
   hand-written reference protocol in `execution/ground_truth/`; then PLR script for OT-2 + plate reader.
7. Trace exporter → demo page; fill slide charts.

---

## 6. Research notes gathered along the way (for slides/related work)
- **Do RAG tricks still matter with reasoning LLMs?** Yes, but the leverage moved: agentic/iterative search and
  precision (reranking, small k) still pay; reasoning models are hurt *more* by distractors (NoisyBench 2601.07226,
  SealQA 2506.01062); long-context stuffing only wins if the KB fits and the model is strong at that length
  (NoLiMa 2502.05167, Li 2407.16833, LaRA 2502.09977); GraphRAG is task-dependent (2502.11371, 2506.05690).
  Hackathon heuristic: small KB → stuff with citations; bigger → hybrid BM25+dense + reranker + search tool, small k.
- **Graph/structured RAG options:** GraphRAG (2404.16130), LightRAG (2410.05779), HippoRAG (2405.14831), Think-on-
  Graph (2307.07697), RoG (2310.01061, fine-tunes), G-Retriever (2402.07630, trains GNN+projector), Ex-GraphRAG
  (2605.21994: interpretable M-GNAN encoder on G-Retriever, LoRA on Llama 3.1 8B, STaRK-Prime; compute not reported),
  text-to-SQL/Cypher/SPARQL, StructGPT, TAG. UniProt SPARQL endpoint sparql.uniprot.org; SIB's LLM→SPARQL work
  (2410.06062).
- **Protocol KG resources:** BAO; ChEMBL assay API (`ebi.ac.uk/chembl/api/data/assay/<id>.json`: assay_type,
  bao_format, cell line, description, target); Opentrons Protocol Library (github.com/Opentrons/Protocols, `.py` +
  `fields.json`; no license file → reference only); LabOP (github.com/Bioprotocols/labop, MIT); BioPlanner
  (2310.10632); BioPIE (2601.04524); WLP; BioProBench (2505.07889).
- **"Next experiment" prior work:** MOOSE-Chem (2410.07076), ResearchBench (2503.21248), SciMON (2305.14259),
  BrainBench (2403.03230), Si et al. (2409.04109), Google AI co-scientist (2502.18864).
- **Literature tools:** Paperclip (GXL; CLI + MCP; 8M+ full-text papers from bioRxiv/medRxiv/arXiv/PMC; API key),
  PaperQA2/3, OpenScholar (2411.14199), PubTator3, Semantic Scholar / OpenAlex / Europe PMC APIs, BioMCP.
These were gathered quickly (some from model knowledge, some web-verified); re-check before citing in the talk.

---

## 7. Practical notes for an agent picking this up
1. Clone the repo, read `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `TODO.md`, then the README of the folder you
   are working in.
2. `pip install -r requirements.txt`; put the Nebius key in `.env`; run `python -m wwtn.llm --models` first.
3. Stay in your folder; build against hand-written JSONL/CSV samples that match `wwtn/schema.py` / `kg/README.md`.
4. Tag anything fake you leave behind with `TODO(final)`.
5. For slide changes: follow `slides/AGENTS.md` (design tokens, no hard-coded colours, no CDNs), run
   `check_deck.py`, look at the pictures in both themes, then push (pushing deploys).
6. Coordinate in Discord before touching `wwtn/schema.py` or another team's folder.
