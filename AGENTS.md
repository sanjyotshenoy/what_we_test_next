# AGENTS.md: instructions for coding agents

Read [README.md](README.md) (what the project is, the layout) and [CONTRIBUTING.md](CONTRIBUTING.md) (the rules)
first. In short:

- Work only in the folder you were asked to work in. Changing `wwtn/` (shared code, above all `wwtn/schema.py`)
  or another workstream's folder needs the person's explicit OK.
- Folders exchange JSON Lines files whose models are in `wwtn/schema.py`; use `read_jsonl` / `write_jsonl`.
- LLM calls go through `wwtn.llm.chat`. Never print, log or commit `NEBIUS_API_KEY` or any `.env` content.
- Run code from the repo root as modules (`python -m <folder>.<module>`).
- Mark anything mock, placeholder or unconfirmed that you leave behind with a `TODO(final): ...` comment at that
  spot (see [TODO.md](TODO.md)); remove it when the real thing is in.
- Work on a branch, and commit + push `WIP: ...` checkpoints after each milestone (say if tests still fail), so
  the team can follow progress; never push to `main` without the person's OK.
- Pushing to `main` redeploys the slides if `slides/` changed; for slide work follow `slides/AGENTS.md` and run
  `check_deck.py` before pushing. Push only when the person asks.

## Commands

There is no linter, no build step and no repo-wide test suite: tests exist only where a folder brought its
own. These are the commands that matter. Nothing in `requirements.txt` is installed by default; use a venv.

```bash
pip install -r requirements.txt && cp .env.example .env   # then fill in NEBIUS_API_KEY
python -m wwtn.llm --models                               # does the key work, which models it reaches
python -m <folder>.<module> ...                           # always from the repo root, never python <path>.py
pip install opentrons && opentrons_simulate <protocol.py> # an OT-2 protocol must run to completion
python slides/tools/check_deck.py slides/talks/biohack    # needed before any push touching slides/
python -m pytest kg                                       # a folder's own tests, where it has them
grep -rn "TODO(final)" --exclude-dir=.git .               # what is still mock, placeholder or unconfirmed
```

## How the folders fit together

One pipeline, six folders, joined **only by files on disk** — no folder imports another's code, so each can be
built against a few hand-written lines of its input while the folder upstream is still empty:

```
benchmark/questions.jsonl ─┐
kg/biology/graph/*.csv     ├─> agent/ ──> agent/out/<run>.jsonl ──> execution/ ──> out/<run>/*.py + results.jsonl
kg/protocols/graph/*.csv  ─┘    (Question -> ExperimentProposal)      (-> OT-2 code -> opentrons_simulate)
                                             │
                      benchmark/ground_truth.jsonl + benchmark.grade  (agent/ must never read ground_truth)
```

Two things make the whole design work, and both are easy to break by accident:

- **Hold-out.** Questions are real ChEMBL activities deleted from the biology KG. Hold out the whole ChEMBL
  *document*, not one edge — analogs from the same paper would hand the agent the answer. `benchmark/held_out.csv`
  is the list `kg/biology/` must obey, and node text/embeddings are built *after* the removal.
- **`TargetClass` is the bridge** between the two graphs (`Target -MEMBER_OF->` ... `<-APPLICABLE_TO- Protocol`),
  so those IDs must match across `kg/biology/` and `kg/protocols/`. The format of both is in `kg/README.md`.

[HANDOFF.md](HANDOFF.md) is the full briefing: every decision made so far, why, and what does not exist yet
(as of 2026-11-07 that is all of the pipeline). Read it before designing anything new.
