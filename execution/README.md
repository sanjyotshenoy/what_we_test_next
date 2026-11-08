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
to the robot. **Atmosphere belongs to a step, not to the lab** — the correction that matters most here. The robot builds the
plate on the bench in a few minutes; a person then carries it to an incubator overnight. Oxygen decides whether
an anaerobe *grows* during the second step, so the panel is checked against `incubation_atmosphere`, while
`liquid_handling_atmosphere` stays plain aerobic because the OT-2 sits on the bench and needs no chamber.

Anaerobic incubation (jars, sachets or an anaerobic incubator) is **assumed**, because the project is
phenotyping anaerobic microbiome bacteria. Assumed capabilities live under `capabilities.assumed` and surface as
a warning on **every** verdict, including the ones that pass, so no result quietly rests on one.

The check runs in **both directions** — an obligate aerobe fails where only anaerobic incubation exists, exactly
as an obligate anaerobe fails with only aerobic — and a species marked `facultative` passes either way. A panel
entry may also declare `oxygen_tolerance`: an **aerotolerant** anaerobe (*B. fragilis*, *C. difficile*,
*B. longum*) survives the minutes on the bench, while a **strictly** oxygen-sensitive one (*F. prausnitzii*) does
not, and is refused with the reason rather than being quietly plated into air.

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

The panel comes from `Experiment.panel` and can still be passed in to override it. An entry is a `PanelMember`
or a plain dict; `atmosphere` may be given directly, or derived from `oxygen_tolerance`.

## The protocol, and the run sheet beside it

`protocol.py` is the last link: the plate map becomes a file the OT-2 accepts.

```python
from execution.protocol import to_ot2, run_sheet, write_protocol, simulate
protocol = to_ot2(design, experiment, Lab.load())
print(protocol.api_level, protocol.tip_columns, protocol.deck, protocol.warnings)
write_protocol(design, "execution/out/q001", experiment, Lab.load(), template)
ok, output = simulate("execution/out/q001/protocol.py")
```

**Two files, not one.** Nothing in the Opentrons API incubates for 18 h at 37 °C in an anaerobic jar, reads
OD590 on the Cytation, or calls the MIC. The robot sets the plate up on the bench in a few minutes and stops.
So `write_protocol` emits `protocol.py` *and* `protocol_run_sheet.md` — the reservoir volumes to pour, the
off-robot steps quoted from the template, the MIC rule, and every assumption `lab.yaml` admits to. A generator
that emitted only the `.py` would be shipping an experiment with no measurement in it.

Everything the generator decides is reported on the result rather than buried in the source: the API level, the
tip columns, the deck assignment, the reservoir volumes, and the warnings. Three checks run on the way:

- `_check_against_transfers` compares the (liquid, volume) movements against the plan `plate.py` made.
- `audit(design)` runs first, so a map that fails its own arithmetic never becomes a protocol.
- `unimplemented_steps(template, ops)` names any **on-robot** verb the template asks for that the command
  sequence does not perform. For `bacterial_mic_broth` this is empty. `TODO(final)`: the command order still
  comes from `plate.py`'s hard-coded MIC sequence, so this reports the gap for other archetypes rather than
  closing it — closing it means driving the order off the template's `steps` tree.

`fit_deck` is the slot arithmetic: plates and tip racks compete for the same 11 slots and grow together, since
each extra plate costs its own tips (14 tip columns at 10 concentrations, so about two racks). Four plates is
the most that fits, and the reservoir is reserved first because it is never the thing to drop.

### Running the simulator

`opentrons` is **not** in `requirements.txt` on purpose — it would break everyone's numpy. It needs its own
environment, and two separate ceilings get confused here:

```sh
python -m venv .venv-sim
.venv-sim/bin/pip install -r execution/requirements-sim.txt
.venv-sim/bin/opentrons_simulate execution/out/q001/protocol.py
```

- `opentrons` imports fail against **numpy ≥ 2** (`cannot import name 'trapz'`), so numpy is pinned below 2.
- `opentrons` **10.x has dropped the OT-2 entirely** — it reports apiLevel 2.31 and then refuses to simulate an
  OT-2 protocol at all. 8.8.2 is the newest release that still runs one, and its ceiling is **2.27**.

`lab.yaml` records `api_level: "2.28"`, which is what the team's own protocol declares, and which no
OT-2-capable simulator understands. `max_api_level()` returns the level we can both generate and check, the
generator drops to it, and says so in a warning. `TODO(final)`: confirm the level from the robot itself.

**One thing the generator cannot work around, and warns about instead.** An 8-channel pipette has no way to
dispense into four of its eight channels: a command addressed at a column fills all eight wells of it. So a
panel of two species at n=2 occupies rows A–D in the plate map while the robot also fills E–H. Those wells are
not wrong — they hold the same series, so they are spare replicates — but they are liquid and tips nobody
planned for, and a person reading the map would not expect them. The same fact is why the reagent estimate
multiplies by every row of the plate rather than the rows the panel uses: a short panel costs as much medium as
a full one. Panels that are a multiple of 8 rows avoid it entirely.

## The whole chain, runnable today

`generate.py` is the executable end of the contract `wwtn/schema.py` already described: proposals in,
protocols out.

```sh
python -m execution.generate agent/out/run1.jsonl --out execution/out/run1 --simulate
python -m execution.generate execution/examples/mic_selectivity.jsonl --simulate     # no API key needed
```

For each `ExperimentProposal` that proposes an experiment it writes `<out>/<question_id>/protocol.py` and
`protocol_run_sheet.md`, and one `ExecutionResult` line into `<out>/results.jsonl`. A proposal the KB already
answers produces nothing — there is no experiment to run. A proposal the lab cannot run produces no protocol
either: `check_feasible`'s violations go into `error`, so the reason is recorded rather than a file that would
fail on the robot.

`execution/examples/mic_selectivity.jsonl` is a hand-written proposal for the four-species selectivity panel —
*C. difficile*, *E. faecalis*, *B. fragilis*, *B. longum* at n=2, which is exactly 8 rows — topped at
256 µg/mL. Ten two-fold steps from there reach 0.5, which sits above the commensals' censored ">128" and below
a typical pathogen MIC, so **one ladder brackets both arms**; it has to, because every row of a plate shares the
same series. 256 rather than a round 200 keeps every rung on the doubling ladder MICs are reported on. It exists
because `agent/` needs `NEBIUS_API_KEY` and no machine here has one: this is how the rest of the chain gets
exercised end to end in the meantime, and it does — the generated protocol simulates clean.
