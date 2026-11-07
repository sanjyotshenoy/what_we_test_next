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
- Pushing to `main` redeploys the slides if `slides/` changed; for slide work follow `slides/AGENTS.md` and run
  `check_deck.py` before pushing. Push only when the person asks.
