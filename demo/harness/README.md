# Planner runtime

See [SETUP](../SETUP.md) for portable installation and commands,
[PIPELINE](PIPELINE.md) for the contract and [memory](../memory/MEMORY.md) for evidence.
The active Python package is `demo.harness`; modules import team contracts directly.
The default OpenCode planner uses only bounded domain tools. The retained legacy
stage tools use seed data and are not biological results. `llm.py` is a legacy
provider utility, not the active planner loop or an automatic stage fallback.


For the configured Brev instance use the [judge runbook](../docs/JUDGE_RUNBOOK.md),
not the old launcher. The operator is on loopback 7100, the read-only judge viewer
on 7200, and internal OpenCode on 4096. Public access remains closed.

The default is explicitly GLM-5.3 with low reasoning effort. `configure_agent.py`
derives the submission tool schema from `planning_pipeline.Batch`; Python still
validates every submission. `biology.py` reads the real bacterial graph, and
`planning_evidence.py` retrieves actual Paperclip passages. Software-test inputs,
simulation results and physical recordings retain separate labels.

`prepare_video.py` creates the local 30-second recording; `stage/recording.py`
serves only the fixed clip and poster to the judge viewer. Media, auth state and
new run artifacts are ignored local files, not included in Git checkpoints.
