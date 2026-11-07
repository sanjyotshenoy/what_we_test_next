# What we test next

**Closing the Loop Between Knowledge and Discovery**: Team Zhang et al., Nucleate Pittsburgh BioHack 2026.

Literature agents can answer a question when someone has already done the experiment. When the honest answer is
**"I don't know"**, we propose the experiment that would answer it (aim 1), grounded in a knowledge graph of
biology and one of experimental protocols, and turn it into a protocol an Opentrons OT-2 can run (aim 2). First
domain: does compound X inhibit target Y, answered by an IC50 dose-response (a serial dilution).

## Layout

Each workstream owns a folder; folders exchange files whose formats are fixed in `wwtn/schema.py` (JSON Lines)
and [kg/README.md](kg/README.md) (graph CSVs). Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first push. New here (or briefing a coding agent)? Start with [HANDOFF.md](HANDOFF.md): the whole project so far in one file; what we have discussed and decided since
is in [DISCUSSIONS.md](DISCUSSIONS.md).

```
benchmark/        questions the KB can't answer (held-out facts), ground truth, grading
kg/biology/       biology KG: compounds, targets, target classes, known activities
kg/protocols/     protocol KG: dose-response templates (steps, parameters, labware), BAO-tagged
agent/            aim 1: question -> "can the KB answer it?" -> ExperimentProposal
execution/        aim 2: ExperimentProposal -> OT-2 protocol -> simulator (and the real robot)
Opentrons/        hand-written reference OT-2 protocols (Emmy): script + written protocol
wwtn/             shared code: llm.py (Nebius calls), schema.py (the data contracts)
slides/           the presentation (live deck)
```

```
benchmark/questions.jsonl --> agent/ <-- kg/biology/graph, kg/protocols/graph
                                |
                     agent/out/<run>.jsonl --> execution/ --> OT-2 protocol + simulation
                                |
                         benchmark/grade (against ground_truth.jsonl)
```

## Calling LLMs (Nebius Token Factory)

`wwtn/llm.py` wraps Nebius's OpenAI-compatible API. Put the key in `.env` (git-ignored; never commit it):

```bash
pip install -r requirements.txt
cp .env.example .env              # then fill in NEBIUS_API_KEY
python -m wwtn.llm --models       # the model IDs the key can use
python -m wwtn.llm "Suggest one follow-up experiment for a CRISPR knockout screen."
```

From Python: `from wwtn.llm import chat; chat("...", model="...", system="...", temperature=0.2)`. The default
model is `NEBIUS_MODEL` in `.env`.

## Slides

**Live deck:** https://zhang-etal-biohack.pages.dev/075d295f820d3892ac1d1010c3ffdc8f31a597f041dc3d2d/talks/biohack/

The link is unlisted: anyone who has it can view the deck, but it is not linked from anywhere or indexed by
search engines, so share it only with people who should see it. The deck is in `slides/talks/biohack/`, built on
[protein-design-interactive-slides](https://github.com/ramithuh/protein-design-interactive-slides) (see
`slides/README.md` and `slides/AGENTS.md`).

- **Demo page:** `slides/talks/biohack/demo/` (also the "Demo" slide, and `demo/` next to the live deck): one
  query through the whole pipeline, played from a trace file. See its README for the trace format.
- **Present locally:** `cd slides && python -m http.server 8000`, then open http://localhost:8000/talks/biohack/
  (or open `slides/talks/biohack/index.html` straight from disk).
- **Check every slide:** `python slides/tools/check_deck.py slides/talks/biohack` (needs Playwright).
- **Deploy:** every push to `main` that touches `slides/` redeploys the link above
  (`.github/workflows/deploy-slides.yml`; needs the `CLOUDFLARE_API_TOKEN` repository secret). By hand:
  `slides/tools/deploy_unlisted.sh zhang-etal-biohack` (needs `wrangler login`). Both keep the same link because
  its random part is committed in `slides/.pages-prefix`.
