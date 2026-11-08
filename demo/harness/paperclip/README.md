# GXL Paperclip for the real-data demo

Paperclip retrieves literature evidence for experiment design (big-picture point 2).
It does not replace the protocol KG, execution compiler or physical robot run.

Official docs: https://paperclip.gxl.ai/docs

Installed locally in `demo/.venv-paperclip/` from GXL's official wheel, version 0.8.16.
The source URL and downloaded SHA-256 are in `install-manifest.json`. This hash
records the artifact we inspected; it is not a separately published signature.
Dependencies are isolated from the harness and OT-2 simulator environments.

From the workspace root:

```bash
demo/harness/paperclip.sh --version
demo/harness/paperclip.sh login
demo/harness/paperclip.sh config
demo/harness/paperclip.sh search -s papers "antibiotic effects on gut microbiota" -n 3 --json
```

`login` uses GXL's device-code flow: open its displayed link on your laptop and
sign into your own account. No SSH callback tunnel is required in this version.
The wrapper sets `PAPERCLIP_CONFIG_DIR` to `demo/harness/paperclip/private/` and a
restrictive umask. OAuth state stays there, ignored by Git. It does not change
global Codex/OpenCode configuration or install a global skill.

For unattended agent use, an API key can instead be set as `PAPERCLIP_API_KEY`,
or saved privately in a terminal on the Spark (never paste it into chat):

```bash
mkdir -p demo/harness/paperclip/private
chmod 700 demo/harness/paperclip/private
(umask 077; read -rs -p 'Paperclip API key: ' paperclip_key; printf '\n';
 test -n "$paperclip_key" && printf '%s' "$paperclip_key" > demo/harness/paperclip/private/api.key)
```

The wrapper reads this file into the environment, never into process arguments.
`config` reports OAuth status, not whether an API key works. A small authenticated
retrieval is the actual connectivity test. Do not display credential files.

## Planning agent integration

OpenCode now has a `planner` agent with evidence tools: `planning_context` (real
team MIC template and lab configuration), `literature_search` (up to 5 papers),
and `literature_read` (up to 60 lines / 12,000 characters). Run it with:

```bash
demo/harness/opencode_server.sh run --agent planner --model nebius/openai/gpt-oss-120b 'YOUR EXPERIMENT-DESIGN QUESTION'
```

The tools run `demo/harness/planning_evidence.py` in the isolated Paperclip venv. Each
successful call saves a session-scoped record under ignored
`demo/harness/planning_runs/<session>/`. Read results include source metadata, exact
returned lines, a passage hash and a citable evidence ID. Search does not expose
the service's generated summaries as source evidence. Timeouts/errors do not
create successful evidence records. Six offline tests cover boundaries and
provenance: `demo/demo/.venv-paperclip/bin/python -m unittest demo.harness.test_planning_evidence`.

The planner submits one proposal per compound with a species panel and field-to-evidence
links through `planning_submit`. Accepted batches are schema-validated and compiled;
`planning_simulate` then checks the generated protocols. See [PIPELINE.md](../PIPELINE.md)
for the contract, checks, pair-specific run strategy and known model orchestration issue.

The legacy `stage` agent remains separate and cannot call these new tools. The
stage server already accepts `STAGE_AGENT=planner` when invoked directly; the
planner UI renders session evidence, proposals and simulation artifacts. This
step does not replace the seed graph in that old demo.

## Evidence contract and remaining work

Start with bounded search and passage retrieval. Preserve paper ID, DOI, date,
source path and passage locations alongside any proposed parameter. Extracted
claims are candidate evidence until checked against the actual passage and assay
context. A search miss is not proof that no measurement exists.

Keep benchmark searches distinct from unrestricted demo research: enforce cutoff
dates and excluded papers before evidence reaches the agent. Unknown publication
dates must not silently pass a benchmark cutoff. The adapter is demo-only;
`HARNESS_EVIDENCE_MODE` set to anything other than `demo` fails closed. Full
benchmark filtering is deferred. Citation IDs demonstrate which text was read,
not that a claim follows from it; field coverage is checked, scientific entailment is not.

The agent may propose multiple species and compounds (e.g. 3 × 3). Compilation
and simulation must represent that design faithfully. The real recorded OT-2 run
remains the separate single-species proof of concept; it is not evidence that the
newly proposed multi-species protocol ran physically.

## Reinstall

Use `python3 demo/install.py` from the repository root. It verifies the pinned
wheel hash and installs locked dependencies in demo/.venv-paperclip. A changed
mutable upstream URL fails closed; review before changing the manifest.
