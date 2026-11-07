# execution/: aim 2, turn the proposal into a protocol the robot runs

**Owner:** _(fill in)_

From an `ExperimentProposal`, generate an Opentrons OT-2 protocol (Python API v2), check that it runs in the
simulator, and, for the demo, run it on the real OT-2 (food colouring into water).

- **Reads:** `agent/out/<run>.jsonl` (`ExperimentProposal`).
- **Writes:** `out/<run>/<question_id>.py` (the protocol) and `out/<run>/results.jsonl` (`ExecutionResult`).
- **Approach:** fill a fixed template built from the official serial-dilution tutorial
  (docs.opentrons.com/v2/tutorial.html) with the proposal's parameters, rather than letting the LLM write free
  code.
- **Checks:** `opentrons_simulate` (`pip install opentrons`) must run it to completion; also volume ≤ the
  pipette's maximum, ≤ 96 wells, enough tips. The simulator catches API and deck errors, not wrong biology.
- **Ground truth:** a hand-written protocol for the same experiment in `ground_truth/`; compare final per-well
  concentrations with the generated one.
- **Run:** `python -m execution.generate --proposals agent/out/kg.jsonl` _(to write)_
