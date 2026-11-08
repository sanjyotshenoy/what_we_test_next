# execution/: aim 2, turn the proposal into a protocol the robot runs

**Owner:** Seh Na <!-- TODO(final): confirm -->

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

## What the lab can do, and whether an experiment fits it

`lab.yaml` describes this lab as a **capability model, not an equipment list**: the instruments, the labware on
hand with its physical limits, and the conditions available. Most of it is read off the team's real OT-2
protocol in [`Opentrons/`](../Opentrons/); everything else carries a `TODO(final)` for whoever is standing next
to the robot. The line that does the most work is `capabilities.atmosphere`. It currently claims **both aerobic and
anaerobic**, on the assumption that the OT-2 sits in a chamber — a real arrangement, but not yet true of this
lab. Assumed capabilities are listed under `capabilities.assumed` and surface as a warning on **every** verdict,
so no result can quietly rest on one. Drop `anaerobic` back out before reporting anything real, or install the
chamber. The check runs in **both directions**: an obligate aerobe (*P. aeruginosa*) fails in an anaerobic-only
setup exactly as an obligate anaerobe (*B. fragilis*) fails in air, and a species marked `facultative` passes
either way.

`feasibility.py` answers "can we run this, and if not, why not" as arithmetic, never a model's opinion:

```python
from execution.feasibility import check_feasible
from execution.lab import Lab
print(check_feasible(experiment, Lab.load(), panel=[{"id": "...", "atmosphere": "anaerobic"}, ...]).sentence())
```

```
Not runnable as proposed: 1 problem(s).
  - 2 species need anaerobic incubation and this lab is aerobic-only: B. fragilis, B. theta
  suggestions:
    * drop the 2 anaerobe(s), or run them by hand (CLSI M11 agar dilution) and flag them for a person
  ! pipette p20_single_gen2 on the right mount may not be installed
```

It checks: atmosphere and temperature against the panel, columns and rows against the plate (so `n_points` +
control columns must fit, and species x replicates decides the plate count), volumes against the plate's working
volume and the pipettes' ranges, tip columns against the racks on hand, medium against the reservoir's usable
capacity (max minus the dead volume the tips cannot reach), and the readout against the reader's modes. A
verdict is never a bare boolean: it names each violation with its numbers, suggests repairs, and reports
anything `lab.yaml` admits is unconfirmed.

## The plate map, and the audit that checks it

`plate.py` turns an experiment plus the panel into the **actual well map** — one row per species per replicate,
the series along the columns, growth and sterility controls last, spilling onto further plates when the panel
outgrows one. It is arithmetic, not generation.

```python
from execution.plate import plate_design, audit
design = plate_design(experiment, Lab.load(), panel)
print(design.render())
assert audit(design) == []
```
```
plate 1 of 1  (2-fold, 10 points, final concentrations in uM)
             1        2        3        4        5        6        7        8        9       10       11       12
  A         64       32       16        8        4        2        1      0.5     0.25    0.125       GC       SC   S. aureus
  B         64       32       16        8        4        2        1      0.5     0.25    0.125       GC       SC   B. fragilis
```

**Every well carries two concentrations, and the distinction is not cosmetic.** Following the team's own
protocol, the compound is prepared at **2×** and an equal volume of inoculum halves it, so `prepared_uM` (128 in
column 1 above) is what sits in the plate during the dilution and `final_uM` (64) is what the cells see.
Reporting one where the other is meant doubles every MIC, and looks entirely plausible — so both are stored, and
`audit()` **replays the transfer plan independently** to check them. It is written not to share arithmetic with
`plate_design`, so a wrong map shows up as a disagreement instead of being echoed back; the tests break the map
on purpose (compound in the growth control, inoculum in the sterility control, a prepared value recorded as
final) and require the audit to object.

`feasible_panel_size(lab, replicates, plates)` is the trade-off in one call: 1 species at n=8 (the current MIC
protocol's layout), or 8 species at n=1, on one plate.

The panel is passed in rather than read off `Experiment`, because the shared schema has no panel field yet
(`TODO(final)`); each entry is `{id, name?, atmosphere?}`.
