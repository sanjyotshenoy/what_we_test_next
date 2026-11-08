"""PlateDesign -> an OT-2 protocol the robot accepts, plus the run sheet for the half it cannot do.

    from execution.plate import plate_design
    from execution.protocol import to_ot2, run_sheet, write_protocol

    design = plate_design(experiment, lab, panel)
    protocol = to_ot2(design, experiment, lab)      # .code is a file opentrons_simulate will run
    print(run_sheet(design, experiment, lab, template))
    write_protocol(design, "execution/out/q001", experiment, lab, template)

Two outputs, deliberately. The OT-2 sets a plate up on the bench in a few minutes and then stops: nothing in
the Python API incubates for 18 h at 37 C in an anaerobic jar, reads OD590 on the Cytation, or calls the MIC.
A generator that emits only the `.py` ships a "protocol" that stops before the measurement, so the off-robot
tail comes out as a run sheet beside it.

Two cross-checks, because a generated protocol that looks right is worth nothing:

  * `to_ot2` rebuilds the command sequence from the design's structure and then compares the volume it moves
    per liquid against `design.transfers`, which `plate.py` produced independently. A disagreement is a bug in
    one of them and shows up as a warning rather than as a wrong plate.
  * `unimplemented_steps` compares the protocol template's on-robot verbs against what the command sequence
    actually does, so a template whose steps we do not implement says so instead of being silently dropped.

TODO(final): the on-robot command order still comes from `plate.py`, which hard-codes the five-step MIC
sequence. `unimplemented_steps` reports the gap for other archetypes but does not close it; closing it means
driving the order off the template's `steps` tree.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from .feasibility import _value
from .lab import Lab
from .plate import GROWTH, STERILITY, PlateDesign, audit

# Verbs a liquid handler can carry out, and verbs that need a person or another instrument. A template step
# tagged with anything in OFF_ROBOT belongs in the run sheet; anything in ON_ROBOT should appear in the code.
ON_ROBOT = {"prepare", "serial_dilute", "dispense", "add", "mix", "transfer", "aspirate"}
OFF_ROBOT = {"incubate", "read", "grow", "measure", "score"}

MEDIUM, COMPOUND, INOCULUM = "medium", "compound", "inoculum"
RESERVOIR_CHANNELS = {MEDIUM: 0, COMPOUND: 1, INOCULUM: 2}

DECK_SLOTS = tuple(range(1, 12))        # 12 is the fixed trash on an OT-2
MIX_REPS = 3                            # matches the team's own protocol


@dataclass
class Op:
    """One command, before it is rendered as Python. Tests assert on these, not on formatted source."""
    kind: str                    # "transfer" | "waste" | "comment"
    liquid: str = ""
    volume_uL: float = 0.0
    source: str = ""             # a reservoir channel name, or a plate column index as a string
    dest: str = ""
    plate: int = 1
    new_tip: str = "always"      # "always" | "never"
    mix_after: bool = False
    text: str = ""


@dataclass
class OT2Protocol:
    code: str = ""
    api_level: str = ""
    ops: list[Op] = field(default_factory=list)
    deck: dict[str, tuple[int, str]] = field(default_factory=dict)   # role -> (slot, load_name)
    tip_columns: int = 0
    tipracks: int = 0
    reservoir_mL: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


OT2_MAX_API_LEVEL = "2.27"
"""The highest apiLevel any OT-2-capable `opentrons` release understands (verified against 8.8.2, 2026-11-08).

Two separate ceilings get confused here, so both are checked. `opentrons` 9.x and 10.x know higher levels but
have dropped the OT-2 entirely - 10.1.0 reports 2.31 and then refuses to simulate an OT-2 protocol at all. So
the newest level the *installed* package knows is not the newest level we can generate: a protocol above
OT2_MAX_API_LEVEL cannot be checked by any simulator that will run it.
"""


def _level(text: str) -> tuple[int, int]:
    major, _, minor = str(text).partition(".")
    return int(major or 0), int(minor or 0)


def max_api_level() -> str:
    """The highest apiLevel we can both generate and simulate for an OT-2."""
    ceiling = OT2_MAX_API_LEVEL
    try:
        from opentrons.protocols.api_support.definitions import MAX_SUPPORTED_VERSION
    except Exception:
        return ceiling      # nothing installed: the documented OT-2 ceiling is still the right answer
    installed = f"{MAX_SUPPORTED_VERSION.major}.{MAX_SUPPORTED_VERSION.minor}"
    return installed if _level(installed) < _level(ceiling) else ceiling


def plan_ops(design: PlateDesign) -> list[Op]:
    """The command sequence, rebuilt from the design's structure in the order the robot performs it.

    The same five steps as the team's protocol: broth into every series column but the first, the two control
    columns, compound at 2x into column 1, the 2-fold carry with the carry-over discarded, then an equal volume
    of inoculum with a fresh tip per column so compound is never carried back into the reservoir.
    """
    n = design.series_columns
    half = design.working_uL / 2
    growth, sterility = n + 1, n + 2
    ops: list[Op] = []

    for plate in range(1, design.plates + 1):
        ops.append(Op("comment", text=f"plate {plate} of {design.plates}", plate=plate))

        # one tip column for all the broth: same liquid, clean source, nothing to carry over
        for column in range(2, n + 1):
            ops.append(Op("transfer", MEDIUM, half, MEDIUM, str(column), plate, new_tip="never"))
        ops.append(Op("transfer", MEDIUM, half, MEDIUM, str(growth), plate, new_tip="never"))
        ops.append(Op("transfer", MEDIUM, design.working_uL, MEDIUM, str(sterility), plate, new_tip="never"))

        ops.append(Op("transfer", COMPOUND, design.working_uL, COMPOUND, "1", plate, new_tip="always"))

        # the dilution chain keeps one tip: it only ever moves the series into itself, most dilute last
        for column in range(1, n):
            ops.append(Op("transfer", "dilution", half, str(column), str(column + 1), plate,
                          new_tip="never", mix_after=True))
        ops.append(Op("waste", "dilution", half, str(n), "trash", plate, new_tip="never"))

        for column in range(1, growth + 1):
            ops.append(Op("transfer", INOCULUM, half, INOCULUM, str(column), plate,
                          new_tip="always", mix_after=True))
    return ops


def tip_columns(ops: Sequence[Op]) -> int:
    """How many tip columns the sequence consumes: one per `new_tip="always"`, plus one per run of `"never"`."""
    used, in_run = 0, False
    for op in ops:
        if op.kind == "comment":
            continue
        if op.new_tip == "always":
            used, in_run = used + 1, False
        elif not in_run:
            used, in_run = used + 1, True
    return used


def reservoir_plan(design: PlateDesign, ops: Sequence[Op], lab: Lab | None = None) -> dict[str, float]:
    """mL to put in each reservoir channel, including the dead volume the tips cannot reach.

    Multiplied by every row of the plate, not by the rows the panel uses: an 8-channel pipette draws on all
    eight channels whatever the map says, so a short panel costs the same reagent as a full one.
    """
    lab = lab or Lab.load()
    dead = float((lab.labware("reservoir") or [{}])[0].get("dead_mL", 0) or 0)
    needed: dict[str, float] = {}
    for op in ops:
        if op.kind == "transfer" and op.liquid in RESERVOIR_CHANNELS:
            needed[op.liquid] = needed.get(op.liquid, 0.0) + op.volume_uL * design.rows / 1000.0
    return {liquid: round(volume + dead, 2) for liquid, volume in needed.items()}


def unimplemented_steps(template: dict | None, ops: Sequence[Op]) -> list[str]:
    """On-robot verbs the template asks for that the command sequence does not perform.

    The honest guard against a one-protocol generator wearing a general-purpose costume: for MIC this comes back
    empty, and for an archetype whose steps we have not implemented it names them.
    """
    if not template:
        return []
    performed = {op.liquid for op in ops} | {"prepare"}      # the 2x compound prep is the reservoir's contents
    if any(op.kind == "transfer" and op.mix_after for op in ops):
        performed.add("mix")
    if any(op.liquid == "dilution" for op in ops):
        performed |= {"serial_dilute", "dispense"}
    if any(op.liquid == INOCULUM for op in ops):
        performed.add("add")

    missing = []
    for step in template.get("steps", []):
        verb = step.get("verb", "")
        if verb in ON_ROBOT and verb not in performed:
            missing.append(f"{verb}: {step.get('text', '')}")
    return missing


def _check_against_transfers(design: PlateDesign, ops: Sequence[Op]) -> list[str]:
    """Check this command sequence against the plan `plate.py` made, independently of how we got here.

    Totals are not comparable: a `Transfer` records a span of columns ("A-H2-A-H10") as one entry, because it
    is the plan a person reads, not a command list. What *is* comparable, and what catches a real mistake, is
    the set of (liquid, volume) movements: dispensing the broth in 150 uL steps when the plan says 100, or
    moving a liquid the plan never mentions, shows up here.
    """
    planned = {(t.what, round(t.volume_uL, 6)) for t in design.transfers}
    ours = {(op.liquid, round(op.volume_uL, 6)) for op in ops if op.kind in ("transfer", "waste")}

    problems = []
    for liquid, volume in sorted(ours - planned):
        problems.append(f"the protocol moves {volume:g} uL of {liquid}, which plate.py does not plan")
    for liquid, volume in sorted(planned - ours):
        problems.append(f"plate.py plans a {volume:g} uL {liquid} movement the protocol does not perform")
    return problems


def rows_in_use(design: PlateDesign, plate: int = 1) -> int:
    """How many of the plate's rows the panel actually occupies."""
    return len({w.row for w in design.wells if w.plate == plate})


def _column_at_a_time(design: PlateDesign) -> list[str]:
    """Warn where the 8-channel pipette fills rows the plate map leaves empty.

    An 8-channel pipette has no way to dispense into four of its eight channels: a command addressed at a
    column fills all eight wells of it. So a panel of two species at n=2 occupies rows A-D in the map while the
    robot also fills E-H. They are not wrong - they hold the same series, so they are spare replicates - but
    they are liquid and tips nobody planned for, and someone reading the map would not expect them.
    """
    short = [plate for plate in range(1, design.plates + 1)
             if 0 < rows_in_use(design, plate) < design.rows]
    if not short:
        return []
    used = rows_in_use(design, short[0])
    spare = [chr(ord("A") + i) for i in range(used, design.rows)]
    return [f"the panel fills {used} of the plate's {design.rows} rows, but an 8-channel pipette fills a whole "
            f"column: rows {spare[0]}-{spare[-1]} will receive the same series as spare replicates. Reduce the "
            f"panel to a multiple of {design.rows}, or record them as replicates"]


def fit_deck(plates_wanted: int, columns_per_plate: int, columns_per_rack: int) -> tuple[int, int]:
    """(plates, tip racks) that fit the OT-2's 11 slots, alongside the one reservoir every plate needs.

    Plates and tip racks compete for the same slots and grow together, because each extra plate needs its own
    tips: at 10 concentrations a plate costs 14 tip columns, so about two racks, and four plates is the most
    that fits. Dropping the reservoir instead is never an option, so it is reserved first.
    """
    room = len(DECK_SLOTS) - 1                      # the reservoir
    plates = max(1, plates_wanted)
    while plates > 1:
        racks = max(1, math.ceil(columns_per_plate * plates / max(1, columns_per_rack)))
        if plates + racks <= room:
            return plates, racks
        plates -= 1
    racks = max(1, math.ceil(columns_per_plate / max(1, columns_per_rack)))
    return 1, min(racks, room - 1)


def _deck(lab: Lab, plates: int, tipracks: int) -> dict[str, tuple[int, str]]:
    """Assign deck slots: the assay plates, then the tip racks, then the reservoir. role -> (slot, load_name)."""
    plate_name = (lab.plate() or {}).get("load_name", "corning_96_wellplate_360ul_flat")
    rack_name = (lab.labware("tiprack") or [{}])[0].get("load_name", "opentrons_96_tiprack_300ul")
    res_name = (lab.labware("reservoir") or [{}])[0].get("load_name", "usascientific_12_reservoir_22ml")

    wanted = [(f"plate{i}", plate_name) for i in range(1, plates + 1)]
    wanted += [(f"tips{i}", rack_name) for i in range(1, tipracks + 1)] + [("reservoir", res_name)]
    return {role: (slot, name) for slot, (role, name) in zip(DECK_SLOTS, wanted)}


def to_ot2(design: PlateDesign, experiment: Any = None, lab: Lab | None = None,
           api_level: str | None = None) -> OT2Protocol:
    """Generate the protocol. Everything it decides is reported on the result, not hidden in the source."""
    lab = lab or Lab.load()
    ops = plan_ops(design)
    per_rack = lab.labware("tiprack")[0]["tips"] // design.rows if lab.labware("tiprack") else 12
    per_plate = tip_columns([op for op in ops if op.plate == 1])
    plates, racks = fit_deck(design.plates, per_plate, per_rack)
    columns_needed = per_plate * plates

    declared = str((lab.instrument("ot2") or {}).get("api_level") or "")
    ceiling = max_api_level()
    level = api_level or (declared if declared and _level(declared) <= _level(ceiling) else ceiling)

    deck = _deck(lab, plates, racks)
    warnings: list[str] = []
    if plates < design.plates:
        warnings.append(f"the panel needs {design.plates} plates, and {plates} plus {racks} tip racks and the "
                        f"reservoir is all that fits the OT-2's {len(DECK_SLOTS)} slots; generated for the "
                        f"first {plates} - the rest need another run")
    warnings += _check_against_transfers(design, ops)
    # a protocol generated from a design whose own arithmetic does not hold is worse than no protocol
    warnings += [f"the plate map does not survive its own audit - {p}" for p in audit(design)]
    warnings += _column_at_a_time(design)
    if declared and _level(declared) > _level(ceiling):
        warnings.append(f"lab.yaml declares apiLevel {declared}, but the highest an OT-2-capable opentrons "
                        f"simulates is {ceiling}; generated at {level} so the protocol can be checked before "
                        f"it runs. Confirm the level from the robot itself")

    available = (lab.labware("tiprack") or [{}])[0].get("count")
    if available is not None and racks > int(available):
        warnings.append(f"{racks} tip racks needed, lab.yaml lists {available}")

    pipette = next((p for p in lab.pipettes() if p.get("channels", 1) > 1), None)
    if pipette is None:
        warnings.append("no confirmed multi-channel pipette in lab.yaml: the column-at-a-time plan needs one")
        pipette = {"model": "p300_multi", "mount": "left"}

    reservoir = reservoir_plan(design, ops, lab)
    usable = lab.reservoir_usable_mL()
    for liquid, mL in reservoir.items():
        if usable and mL > usable:
            warnings.append(f"{liquid}: {mL} mL needed, one reservoir channel holds {usable:g} mL usable")

    protocol = OT2Protocol(api_level=level, ops=ops, deck=deck, tip_columns=columns_needed, tipracks=racks,
                           reservoir_mL=reservoir, warnings=warnings)
    protocol.code = _render(design, protocol, pipette, experiment)
    return protocol


def _render(design: PlateDesign, protocol: OT2Protocol, pipette: dict, experiment: Any) -> str:
    """Render the ops as an OT-2 API v2 file. The plate map goes in the docstring so the file can be reviewed."""
    deck = protocol.deck
    plate_load = deck["plate1"][1] if "plate1" in deck else ""
    rack_load = deck["tips1"][1] if "tips1" in deck else ""
    res_load = deck["reservoir"][1]
    rack_slots = [deck[f"tips{i}"][0] for i in range(1, protocol.tipracks + 1) if f"tips{i}" in deck]

    map_lines = "\n".join("    " + line for line in design.render().splitlines())
    reservoir_lines = "\n".join(f"    {liquid}: {mL} mL in channel {RESERVOIR_CHANNELS[liquid] + 1}"
                                for liquid, mL in sorted(protocol.reservoir_mL.items()))
    warn_lines = "\n".join(f"    WARNING {w}" for w in protocol.warnings)

    lines = [
        '"""Generated by execution/protocol.py from the plate map below. Do not edit by hand: edit the',
        "experiment or lab.yaml and generate again.",
        "",
        "This file is the on-robot half only. Incubation, the plate read and the MIC call are in the run",
        "sheet beside it; the robot stops once the plate is set up.",
        "",
        map_lines,
        "",
        "Reservoir:",
        reservoir_lines or "    (none)",
    ]
    if warn_lines:
        lines += ["", warn_lines]
    lines += ['"""']

    name = f"MIC {design.fold:g}-fold, {design.series_columns} points, {len(design.species())} species"
    lines += [
        "",
        "metadata = {",
        f'    "protocolName": {name!r},',
        '    "author": "what_we_test_next (generated)",',
        f'    "description": {f"{design.series_columns}-point {design.fold:g}-fold series, top final "
                              f"{design.top_final_uM:g} {design.unit}"!r},',
        "}",
        f'requirements = {{"robotType": "OT-2", "apiLevel": "{protocol.api_level}"}}',
        "",
        "",
        "def run(protocol):",
        f'    tips = [protocol.load_labware({rack_load!r}, slot) for slot in {tuple(rack_slots)!r}]',
        f'    pipette = protocol.load_instrument({pipette["model"]!r}, {pipette["mount"]!r}, tip_racks=tips)',
        f'    reservoir = protocol.load_labware({res_load!r}, {deck["reservoir"][0]})',
    ]
    for liquid, channel in sorted(RESERVOIR_CHANNELS.items(), key=lambda kv: kv[1]):
        if liquid in protocol.reservoir_mL:
            lines.append(f"    {liquid} = reservoir.columns()[{channel}][0]")
    for plate in range(1, design.plates + 1):
        role = f"plate{plate}"
        if role in deck:
            lines.append(f"    plate{plate} = protocol.load_labware({plate_load!r}, "
                         f"{deck[role][0]}).columns()")
    lines.append("")

    open_tip = False
    for op in ops_for_render(protocol.ops, deck):
        if op.kind == "comment":
            if open_tip:
                lines.append("    pipette.drop_tip()")
                open_tip = False
            lines += ["", f"    protocol.comment({op.text!r})"]
            continue
        dest = f"plate{op.plate}[{int(op.dest) - 1}][0]" if op.dest.isdigit() else op.dest
        source = (f"plate{op.plate}[{int(op.source) - 1}][0]" if op.source.isdigit() else op.source)
        if op.kind == "waste":
            if not open_tip:
                lines.append("    pipette.pick_up_tip()")
                open_tip = True
            # dispensed into the trash rather than carried there inside the tip, which drips
            lines += [f"    pipette.aspirate({op.volume_uL:g}, {source})",
                      "    pipette.dispense(%g, protocol.fixed_trash)" % op.volume_uL,
                      "    pipette.drop_tip()", ""]
            open_tip = False
            continue
        if op.new_tip == "never":
            if not open_tip:
                lines.append("    pipette.pick_up_tip()")
                open_tip = True
            mix = f", mix_after=({MIX_REPS}, {op.volume_uL:g})" if op.mix_after else ""
            lines.append(f'    pipette.transfer({op.volume_uL:g}, {source}, {dest}, new_tip="never"{mix})')
        else:
            if open_tip:
                lines.append("    pipette.drop_tip()")
                open_tip = False
            mix = f", mix_after=({MIX_REPS}, {op.volume_uL:g})" if op.mix_after else ""
            lines.append(f'    pipette.transfer({op.volume_uL:g}, {source}, {dest}, new_tip="always"{mix})')
    if open_tip:
        lines.append("    pipette.drop_tip()")
    return "\n".join(lines) + "\n"


def ops_for_render(ops: Sequence[Op], deck: dict[str, tuple[int, str]]) -> list[Op]:
    """Drop the ops for plates that did not fit the deck, so the generated file matches what it loads."""
    return [op for op in ops if f"plate{op.plate}" in deck]


def run_sheet(design: PlateDesign, experiment: Any = None, lab: Lab | None = None,
              template: dict | None = None) -> str:
    """The part the robot cannot do, as markdown: what to prepare, what to incubate, what to read, what to call.

    Everything here is quoted from the template or from lab.yaml rather than written fresh, so a person can
    check it against the source. Where the lab's capability is assumed rather than confirmed, it says so.
    """
    lab = lab or Lab.load()
    protocol = to_ot2(design, experiment, lab)
    unit = design.unit
    lines = [f"# Run sheet - {len(design.species())} species, {design.series_columns}-point "
             f"{design.fold:g}-fold series",
             "",
             "Generated beside the OT-2 protocol. The robot does the liquid handling; these steps are yours.",
             "",
             "## Before the robot", ""]

    for liquid, mL in sorted(protocol.reservoir_mL.items()):
        lines.append(f"- **{liquid}** - {mL} mL into reservoir channel {RESERVOIR_CHANNELS[liquid] + 1} "
                     f"(includes the {(lab.labware('reservoir') or [{}])[0].get('dead_mL', 0)} mL the tips "
                     f"cannot reach)")
    lines.append(f"- the compound goes in at **{design.top_final_uM * 2:g} {unit}**, twice the top assay "
                 f"concentration, because the inoculum doubles the volume and halves it")
    for step in (template or {}).get("steps", []):
        if step.get("verb") in ("prepare", "grow") and "inocul" in step.get("text", "").lower():
            lines.append(f"- {step['text']}")

    lines += ["", "## Plate map", "", "```", design.render(), "```", "", "## After the robot", ""]
    for step in (template or {}).get("steps", []):
        if step.get("verb") in OFF_ROBOT:
            lines.append(f"- **{step['verb']}** - {step.get('text', '')}")
    if not any(step.get("verb") in OFF_ROBOT for step in (template or {}).get("steps", [])):
        temperature = _value(experiment, "incubation_C", 37) or 37
        lines += [f"- **incubate** - about 18 h at {temperature} C",
                  "- **read** - turbidity (OD590), or score visible growth by eye",
                  "- **call the MIC** - the lowest concentration with no growth"]

    for analysis in (template or {}).get("analysis", []):
        lines.append(f"- **analysis** - {analysis.get('text', '')}")

    wanted = _value(experiment, "atmosphere")
    if wanted:
        # the person carrying the plate to the incubator is the one who has to act on this
        lines.append(f"- **atmosphere** - incubate **{wanted}**; this lab has "
                     f"{', '.join(sorted(lab.atmospheres('incubation'))) or 'nothing recorded'}")

    assumed, unconfirmed = lab.assumed(), lab.unconfirmed()
    if assumed or unconfirmed or protocol.warnings:
        lines += ["", "## Check before trusting a result", ""]
        seen: set[str] = set()
        for key, why in assumed.items():
            text = " ".join(why.split())
            seen.add(text)
            lines.append(f"- **assumed** {key}: {text}")
        for item in unconfirmed:
            # lab.unconfirmed() repeats the assumptions above; say each thing once
            if not any(text in item for text in seen):
                lines.append(f"- **unconfirmed** {item}")
        for warning in protocol.warnings:
            lines.append(f"- **warning** {warning}")

    missing = unimplemented_steps(template, protocol.ops)
    if missing:
        lines += ["", "## Steps the generated protocol does not perform", ""]
        lines += [f"- {m}" for m in missing]
    return "\n".join(lines) + "\n"


def write_protocol(design: PlateDesign, out_dir, experiment: Any = None, lab: Lab | None = None,
                   template: dict | None = None, stem: str = "protocol") -> dict[str, str]:
    """Write `<stem>.py` and `<stem>_run_sheet.md` into `out_dir`; return the paths and the warnings."""
    from pathlib import Path

    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    protocol = to_ot2(design, experiment, lab)
    py = directory / f"{stem}.py"
    md = directory / f"{stem}_run_sheet.md"
    py.write_text(protocol.code, encoding="utf-8")
    md.write_text(run_sheet(design, experiment, lab, template), encoding="utf-8")
    return {"protocol": str(py), "run_sheet": str(md), "warnings": protocol.warnings,
            "api_level": protocol.api_level}


def simulate(path) -> tuple[bool, str]:
    """Run `opentrons_simulate` on a generated file: (ok, the simulator's output or the reason it could not run).

    Kept out of the test suite's hot path on purpose. `opentrons` needs numpy < 2 and a release that still
    supports the OT-2 (8.8.2 does; 10.x has dropped it), so it lives in its own environment and this returns
    False with an explanation rather than failing when it is not installed. See execution/README.md.
    """
    import subprocess
    try:
        done = subprocess.run(["opentrons_simulate", str(path)], capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return False, "opentrons_simulate is not on PATH; see execution/README.md for the pinned environment"
    except subprocess.TimeoutExpired:
        return False, "opentrons_simulate timed out after 300 s"
    # the simulator reports a protocol error on stderr and still exits 0 in some versions, so check both
    stderr = done.stderr or ""
    failed = done.returncode != 0 or "Traceback" in stderr or "Error" in stderr
    return not failed, (done.stdout or "") + stderr


__all__ = ["OT2Protocol", "Op", "to_ot2", "run_sheet", "write_protocol", "plan_ops", "tip_columns",
           "reservoir_plan", "unimplemented_steps", "max_api_level", "simulate", "GROWTH", "STERILITY"]
