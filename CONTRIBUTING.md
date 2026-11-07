# Working in this repo

Seven people, two days, one repo. These rules keep us out of each other's way.

## Stay in your folder

Each workstream owns one top-level folder (see the layout in [README.md](README.md)). Inside it, do what you
like. Outside it, ask first:

- **`wwtn/`** is shared code that everyone imports (`llm.py`, `schema.py`). Post in Discord before changing it,
  above all `schema.py`: it is the contract between folders.
- **`slides/`**: every push to `main` that touches it redeploys the live deck. Run
  `python slides/tools/check_deck.py slides/talks/biohack` first.
- **`README.md`, `requirements.txt`**: add to them; don't rewrite other people's parts.

## Folders talk through files

A workstream reads and writes **JSON Lines files whose models are in `wwtn/schema.py`**, not each other's
internals. So you can start before the folder upstream of you is done: write a few lines by hand that match the
schema, and build against those. Knowledge graphs use the node/edge CSV format in [kg/README.md](kg/README.md).

## Git

- Commit small and often; `git pull --rebase` before you push. Pushing straight to `main` is fine when you only
  touched your own folder. For changes to shared files, use a branch and a PR, or say so in Discord first.
- **Never commit secrets.** API keys go in `.env` (git-ignored); see `.env.example`.
- **Data:** small files (under ~10 MB) can be committed, in your folder's `data/`. Anything bigger goes in a
  `data/raw/` folder (git-ignored); commit the script that downloads it instead.
- Generated output goes in your folder's `out/` (git-ignored) unless others need it; then commit it and say so.

## Code

- Python 3.10+. Add dependencies to `requirements.txt` (with a lower bound) when you add an import.
- Run things as modules from the repo root, `python -m agent.propose ...`, so `import wwtn` works everywhere.
- Every folder keeps a short `README.md`: what it does, who owns it, how to run it, what it writes.
- LLM calls go through `wwtn.llm.chat` so we can switch models in one place and compare them fairly.

## Things to finish before presenting

Anything that is mock, placeholder or unconfirmed carries a `TODO(final)` comment where it lives, so nothing fake
ends up on screen. Add one whenever you leave such a thing behind, and list what is left with
`grep -rn "TODO(final)" --exclude-dir=.git .` (see [TODO.md](TODO.md)).

## Coding agents

Claude Code, Codex and others read [AGENTS.md](AGENTS.md); keep it in step with this file.
