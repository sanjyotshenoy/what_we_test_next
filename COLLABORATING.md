# Working with agents as a team

A setup for a team that shares one repo and talks to coding agents (Claude Code, Codex and others) both locally
and through the Discord bridge. It comes from what slowed us down at BioHack 2026 and is meant to be copied into
other projects too. Nothing here is set up in this repo yet; the last section lists the steps.

**What went wrong, and which part of this guide fixes it:**

| Problem we hit | Fix |
| --- | --- |
| A new Discord thread starts a fresh agent session, and people assumed it knew the parent channel's context | [Thread brief and handoff](#5-discord-one-task-per-thread-a-brief-to-start-a-handoff-to-finish) |
| Decisions were buried in chat, and agents couldn't tell a suggestion from an agreed decision | [DISCUSSIONS.md states](#4-discussionsmd-decisions-with-a-state-and-a-source) |
| Docs lagged behind the code: `HANDOFF.md` still says no pipeline code exists, but PR #4 merged it | [STATUS.md](#3-statusmd-what-is-true-now) |
| Each agent's memory sits on one machine (`~/.claude`, Codex's home), so other people's agents never see it | [Shared memory files](#2-memoryhandlemd-what-an-agent-should-know-about-you) |
| Two branches both appended to `DISCUSSIONS.md` and conflicted | [One log file per person per day](#1-loghandleyyyy-mm-ddmd-your-daily-log) |

## The layout

```
AGENTS.md                  the one set of agent instructions (see section 0)
CLAUDE.md                  one line: @AGENTS.md
STATUS.md                  what is true now, one section per workstream, overwritten
DISCUSSIONS.md             decisions over time, appended (already exists)
TODO.md                    TODO(final) convention (already exists)
memory/<handle>.md         what an agent should know about each person
log/<handle>/YYYY-MM-DD.md each person's daily log
```

Everything in these files is visible to anyone with access to the repo. Never put keys, `.env` content, or
anything you wouldn't say in #general in them.

---

## 0. AGENTS.md and CLAUDE.md: one source of truth

Codex (and most other agent tools) read `AGENTS.md`. Claude Code reads `CLAUDE.md`. You want one set of rules
that every tool reads. There are three ways to get that:

| Option | How | Trade-off |
| --- | --- | --- |
| **A. Recommended: `AGENTS.md` is the real file; `CLAUDE.md` imports it** | `CLAUDE.md` contains the line `@AGENTS.md` | Works on every OS and every git setting. Claude Code loads the imported file automatically. You can add Claude-only notes below the import. |
| B. Symlinks to `PROJECT.md` | `ln -s PROJECT.md AGENTS.md && ln -s PROJECT.md CLAUDE.md` | Fine on macOS and Linux. On Windows, or anywhere git has `core.symlinks=false`, the checkout gets a text file that contains only the word `PROJECT.md`, and the agent silently loses its instructions. Some web views and editors don't follow links. |
| C. Symlink `CLAUDE.md` → `AGENTS.md` | `ln -s AGENTS.md CLAUDE.md` | Same symlink caveats as B, with one fewer file. |

Option A gets you what the `PROJECT.md` approach gets you without needing symlinks. `AGENTS.md` is already the
name other tools look for, so it can be the true file itself. If you prefer B, it's fine as long as everyone on
the project uses macOS or Linux.

**One fix for this repo:** `CLAUDE.md` currently says `See [AGENTS.md](AGENTS.md).` A markdown link is only text.
Claude reads `AGENTS.md` only if it decides to follow the link. Change that line to `@AGENTS.md` so the file
always loads. (Newer Claude Code versions may read `AGENTS.md` on their own; the import is harmless if so.)

**Nested files:** both tools also read instruction files in subfolders when working there (here:
`slides/AGENTS.md` + `slides/CLAUDE.md`). Put the same import line in each subfolder's `CLAUDE.md`.

**What belongs in `AGENTS.md`:** agents load it at the start of every session, so keep it short (under ~150
lines). It should hold rules ("run X before pushing", "never touch Y"), the repo layout, and links to longer
docs. It should not hold project knowledge or history; those go in `STATUS.md`, `DISCUSSIONS.md` and folder
READMEs, which agents read when they need them.

**Personal preferences** ("I like short answers", "always use uv") go in your own `~/.claude/CLAUDE.md` or
`~/.codex/AGENTS.md`, not in the shared file. Or put them in `memory/<handle>.md` (below) if you want every
agent, including the one in Discord, to know them.

---

## 1. `log/<handle>/YYYY-MM-DD.md`: your daily log

Each person gets one file per day. Because no two people ever edit the same file, there are no merge conflicts.
Write it yourself, or have the agent append an entry at the end of a task (see the rules in section 6).

```markdown
# 2026-11-12, alice   (example)

- Built candidate generator v0 on branch `candidates` (`screening/candidates.py`). Not yet checked against
  ChEMBL MICs.
- Decided with bob: commensal panel = 3 strains (→ DISCUSSIONS.md 2026-11-12).
- Blocked: need the bacterial KG export from kg/biology.
- Tomorrow: MIC ratio filter.
```

Keep entries to facts: what you did, where it lives (file, branch or PR), what's blocked, and what's next. An
agent asked "what is alice working on?" reads your last 3 to 5 files.

## 2. `memory/<handle>.md`: what an agent should know about you

You write this and keep it current. Agents read it but don't change it without asking you. It answers the
questions an agent would otherwise ask you, or get wrong.

```markdown
# alice   (example)

- **Role:** owns the problem framing and the candidate-generation step.
- **Owns:** `screening/`. Reviews changes to `wwtn/schema.py`.
- **Current focus:** pathogen-vs-commensal selectivity (see STATUS.md → Screening).
- **How I work:** short answers first, detail on request. Show me the diff before committing to my folders.
  Tell me what you verified by running it vs what you read.
- **Don't:** push to main for me; change `kg/` without asking bob.
- **Context an agent wouldn't guess:** "MIC" in my messages always means µg/mL unless stated.
```

This file holds stable facts, not a diary; the diary goes in `log/`. Keep it to about 20 lines.

## 3. `STATUS.md`: what is true now

There is one section per workstream. Edit your section in place rather than appending to it. Each claim gets a
date and says how it was checked.

```markdown
## Execution (owner: carol · branch: main)   <!-- example -->
- **Works:** plate map → OT-2 .py that simulates clean. *Verified 2026-11-08: ran `pytest execution/`, all pass.*
- **Doesn't yet:** agent → execution hand-off for bacterial MIC. *Read in code 2026-11-12, not run.*
- **Waiting on:** agent emitting `Experiment` with a species panel.
```

Use one heading per workstream, not one big table. Git reports a conflict when two people edit neighbouring
lines, so a table where everyone edits adjacent rows conflicts constantly. Separate sections merge cleanly. The
"verified by running" vs "read in code/docs" note is the single most useful habit here: it stops a stale summary
from being repeated as fact.

## 4. `DISCUSSIONS.md`: decisions with a state and a source

This file already exists and works well. Two additions:

- A fourth state, **superseded**, which links to the entry that replaces it. Never delete old decisions; agents
  need to know a decision changed, not just what the current one is.
- A **source** for each entry: a Discord message link, meeting date or PR. This keeps a "suggested" idea from
  quietly turning into a "decided" fact as it gets summarized from one place to the next.

```markdown
**Commensal panel** (Discord, <message link>). Decided: 3 strains. Supersedes 2026-11-08 "one strain only".   (example)
```

## 5. Discord: one task per thread, a brief to start, a handoff to finish

How the bridge works: **each channel or thread is its own agent session.** A new thread does *not* inherit the
parent channel's history. Everyone in a channel shares that channel's one session.

- **#general is for agreed state and quick questions**, not for work. Start a thread for each task.
- **Open each thread with a brief** (paste this and fill it in):

  ```
  @bot
  Goal: <one sentence, the deliverable>
  Context: STATUS.md → <section>; DISCUSSIONS.md → <entry>; branch <name>
  Constraints: <what not to touch, who must review>
  Done when: <a check, e.g. "tests pass and a simulated run log is attached">
  ```

- **Close each thread with a handoff.** Ask the agent to "close this out". It replies with what changed, the
  evidence, what's still open, and which earlier decisions it replaces. It also updates `STATUS.md`, your log,
  and `DISCUSSIONS.md` if something was decided. Post that summary in #general.
- **One owner per thread.** If someone else wants to redirect the work, they say so explicitly ("replacing the
  earlier ask: ..."), so the agent isn't steered two ways at once.
- **Name the thing.** Write "update `screening/README.md` with the panel" rather than "do it". Attach files to
  the same message as the request.

Separate Discord sessions do **not** isolate files: they all edit the same checkout. An agent that edits code
should work on its own branch or git worktree, so two threads never edit the same files at once.

## 6. Rules to add to AGENTS.md

Paste this block into `AGENTS.md` so every agent, local or Discord, follows the same routine:

```markdown
## Team memory
- At the start of a task, read `STATUS.md`, the requester's `memory/<handle>.md`, and their last few
  `log/<handle>/` files. Ask if the requester's handle isn't clear.
- When you finish a task, append a short entry to the requester's log for today (`log/<handle>/YYYY-MM-DD.md`)
  and update the affected section of `STATUS.md`. If a decision was made, add it to `DISCUSSIONS.md` with its
  source.
- In STATUS.md and in replies, date every claim and say whether you verified it by running something or read
  it in code/docs.
- Don't edit someone's `memory/` file without their OK; propose the change instead.
- Never write secrets, `.env` content, or content from private channels into these files.
```

---

## Setting this up in this repo

1. Change `CLAUDE.md` and `slides/CLAUDE.md` to the single line `@AGENTS.md`.
2. Create `memory/` and `log/`, each with a `README.md` holding the template above. Each person adds their own
   `memory/<handle>.md`.
3. Write the first `STATUS.md` from what's actually on `main` (run the tests and record the result). Mark
   `HANDOFF.md` as a historical snapshot from 2026-11-07.
4. Paste the section 6 block into `AGENTS.md`, and add *superseded* to the states listed at the top of
   `DISCUSSIONS.md`.
5. Pin the thread-brief template in #general.

An agent can do steps 1 to 4 on a branch in one go. Step 2's personal files are better written by each person,
or drafted by an agent and corrected by the person.
