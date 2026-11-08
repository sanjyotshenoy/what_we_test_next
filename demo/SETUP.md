# Portable planner setup

This is the active Ouroboros runtime. It uses this repository's `wwtn`, `execution`
and `kg` modules without modifying them. No second checkout, inherited virtualenv,
OpenCode profile, model weights or local Qwen server is required.

## Existing Brev deployment

For the already configured `biohackdemo` VM, read the
[current remote handoff](memory/REMOTE_HANDOFF.md) first. It uses systemd services,
not the tmux launcher below. Do not start both. Authentication is configured on that
VM; three consecutive fresh autonomous rehearsals now pass with the final GLM
settings. Earlier failures are preserved in the verification log. The installation and
historical verification instructions below also apply to new clean deployments.

## Install

Verified target: Linux aarch64 (DGX Spark), Python 3.12. Other OS/architectures are
not validated; use a browser against the Spark or review a matching official
OpenCode release asset before extending the installer. The Python/UI code is
portable; the pinned binary manifest is intentionally platform-specific.

Prerequisites: Python 3.12, `uv` on PATH, Git, internet access to package indexes,
GitHub releases and GXL. Optional launcher: bash, tmux, curl, iproute2 (`ss`).
From the repository root:

```bash
python3 demo/install.py --dev
# Optional browser verification; system Chromium dependencies must also be present:
demo/.venv/bin/python -m playwright install chromium
```

The installer creates only demo-local environments and state. Runtime dependencies
are in `requirements.txt`; exact transitive resolutions are in `requirements.lock`.
Development/browser, Paperclip and simulator environments have separate locks.
The minimal runtime covers imported team modules; use the repository's top-level
requirements separately for other workstreams. No GPU libraries are required.

OpenCode 1.19.5 and GXL Paperclip 0.8.16 downloads are checked against the manifests
in `harness/{opencode,paperclip}/`. A changed Paperclip wheel URL fails with a hash
mismatch; do not bypass it or silently upgrade. OpenCode's embedded dependency
installer bootstraps `.opencode/package-lock.json`; plugin 1.19.5, SDK 2.0.41 and Zod 4.6.7
are pinned. The launcher derives the submission tool schema from the Python validator. `OPENCODE_CONFIG_DIR` plus disabled project/Claude discovery prevents
loading contributor or parent-workspace tools. The runtime config is generated
with this checkout's provider URL and prompts, never a committed absolute path.

The simulator lock derives from `execution/requirements-sim.txt`: opentrons 8.8.2,
numpy 1.26.4, API ceiling 2.27. Do not combine it with the main environment or
upgrade to Opentrons 9/10 for an OT-2 demo.

## Authentication and live operation

Use your own credentials. None are copied by setup. For Nebius, either copy
`.env.example` to `demo/.env`, set permissions to 600 and fill it in locally, or
use the planner's Keys panel. Never paste secrets into chat or commit them.
Paperclip needs its own login:

```bash
demo/harness/paperclip.sh login
# Device URL can be opened on your laptop; private state stays under demo/.
demo/harness/paperclip.sh search -s papers 'broth microdilution' -n 1 --json
demo/harness/stage.sh start
```

Open `http://127.0.0.1:7100/`, or the host's Tailscale IP on port 7100. The server
binds loopback and an available Tailscale IPv4, not public interfaces. Treat access
to that tailnet as access to the demo (including key management). The backend
OpenCode API binds loopback with a generated password. Alternate ports:
`STAGE_PORT=7102 OPENCODE_PORT=4098 demo/harness/stage.sh start`.

The launcher owns a checkout-specific tmux session; `stage.sh status` and
`stage.sh stop` inspect/stop only that session. For foreground operation, run
`demo/harness/opencode_server.sh` in one terminal and
`demo/.venv/bin/python -m demo.harness.stage.server` from the repo root in another.
Stop both with Ctrl-C. No local model or robot is started.

Default agent/model: OpenCode `planner`, Nebius `zai-org/GLM-5.3`, low reasoning
effort, temperature 0, 16,384 output tokens and at most 16 model steps. GPT-OSS
remains a manual alternative; it is not an automatic fallback. See the
[judge runbook](docs/JUDGE_RUNBOOK.md) for the verified private configuration. The custom
provider requests one complete response and adapts it to SSE because upstream
streaming omitted tool metadata. No retry/model substitution occurs. Activity
updates per tool/model turn. Attempt limits persist per session: context 3,
search 3, passages 6, bacterial lookups 3, submissions 3, simulation 1. Failed
calls consume attempts. Start a new session only after reviewing a failure.

Optional Qwen: configure the existing external endpoint/model in the demo's
OpenCode config and use `PUT /auth/spark-qwen` followed by `POST /instance/dispose`
with its key. It is a manually selected provider, not automatic stage failover.
No GPU downloads or machine-specific Qwen launcher are part of this demo.

## Verification and fallback

```bash
demo/.venv/bin/python -m unittest demo.harness.test_planning_pipeline demo.harness.test_reliability demo.harness.test_biology demo.harness.test_tool_stream
demo/.venv-paperclip/bin/python -m unittest demo.harness.test_planning_evidence
demo/.venv/bin/python -m demo.harness.smoke --simulate
DEMO_REPLAY=1 demo/.venv/bin/python -m demo.harness.stage.server
```

The smoke test compiles/simulates four synthetic compound/species pairs through
the real team compiler. It is a **direct backend test, not autonomous success**.
Outputs live in ignored `demo/harness/planning_runs/<session>/`: proposal JSONL,
field evidence, source maps, plate maps, run sheets, protocols, rule checks and
simulator reports. Each protocol/report hash must match to display a pass.

Replay mode needs no live backend or credentials. Select the recorded session
in View; it displays the real 2026-11-07 retrieval/simulation artifacts with
synthetic inputs. Live actions are disabled. Provenance and original hashes live
in `replays/provenance.json`; no agent database is shipped. This is explicit saved
evidence, not a new run. Stop the foreground replay server with Ctrl-C.

For a live smoke, start the backend, configure both credentials, click **Load
software rehearsal**, then **Run planning agent**. Expect real context/search/read,
submission and four simulations. Check all four source identities, plate maps,
report hashes and completed agent answer. Keep synthetic labels. Do not manually
edit artifacts and then call the run autonomous. A new biological question still
needs a reviewed panel, evidence applicability and required controls.

The original `demo/index.html?theme=dark` and slide symlink remain unchanged.
They use the existing trace/agent.server interface. Port 7100 serves the planner;
`/legacy` retains the seed demo UI and needs `STAGE_AGENT=stage` to use its tools.
Do not use the legacy page with the planner and expect its panels to populate.

## Failures and limits

- Missing auth: configure that service; installation deliberately has no credentials.
- Hash mismatch: inspect the changed upstream artifact before updating a manifest.
- Port busy: choose both alternate ports; never stop an unidentified process.
- Simulator timeout: inspect its saved log/environment before retrying. Restricted
  process sandboxes can prevent simulator or Chromium startup.
- Graph missing identity: supply exact IDs/names; absence in this graph is not proof
  of a scientific gap. MICs preserve censoring, units and assay/document provenance.
- Unsupported controls/layouts: retain the requirement and stop; do not remove it
  to force compilation. Citation identity is not scientific entailment. Simulation
  is not biological validation or physical execution.

See [current memory](memory/MEMORY.md) and [remaining work](docs/PIPELINE_TODO.md).
