# Evidence snapshot for the presentation

Audited source: `main` commit `30886d3`, 2026-11-08. Generated files in this folder expose the specific example used in the deck; they are research artifacts, not instructions approved for wet-lab use.

- Biology CSV counts were recomputed; SHA-256 hashes are in `data.json`.
- Full test run: `python -m pytest -q` with root requirements: **340 passed, 3 skipped**. No LLM calls. The simulator was then checked separately.
- Simulation: `python -m execution.generate execution/examples/mic_selectivity.jsonl --out /tmp/wwtn-mic-evidence --simulate`, with `opentrons==8.8.2`, `numpy<2`, pydantic and pyyaml: **passed**. API 2.27, with warnings retained in `result.json` and `run_sheet.md`.
- `input.jsonl` is the committed **hand-written** four-species example. It is not an agent output.
- `protocol.py` and `run_sheet.md` are generated outputs; `data.json` contains the calculated plate and independent audit result.
- Refresh: `python -m slides.tools.prep_deck_evidence --execution-dir /tmp/wwtn-mic-evidence` from the repository root, after rerunning generation and simulation.

## Presentation choices

Lead with microbial selectivity, then show the graph's measurement provenance, rule provenance, plate arithmetic and inspectable generated artifacts. Explain graph retrieval, LLM orchestration and future feedback loops at high level. Keep source identifiers and checks in the evidence links and notes.

The old placeholder slides, empty benchmark charts and recorded animated demo remain in source but are not loaded in this evidence-focused deck. The graph/case viewer is loaded instead. It contains real records and diagnostic cases, not completed model evaluations.

## Limits to state

The MIC graph is not connected to the default kinase-oriented agent query path. The three case packets test kinase/cellular reasoning and still need reviewer calibration. There is no scored MIC model comparison or completed wet-lab result. The executor currently warns rather than hard-stops on audit failures, non-two-fold transfers are not supported correctly, unknown oxygen tolerance is optimistic, and hardware/culture conditions require confirmation.
