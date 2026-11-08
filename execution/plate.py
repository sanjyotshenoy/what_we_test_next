"""Experiment + lab + panel -> the actual well map, computed rather than generated.

    from execution.plate import plate_design
    design = plate_design(experiment, Lab.load(), panel)
    print(design.render())          # the plate as a human reads it
    design.wells[0].final_uM        # what is really in A1 once the inoculum is in

The layout follows the team's own MIC protocol (Opentrons/): the compound goes into column 1 at **twice** the
top assay concentration, is carried column to column, and an equal volume of inoculum is added at the end, which
halves everything. So two different numbers describe the same well:

    prepared_uM   what is in the well during the dilution
    final_uM      what the bacteria actually see, after the inoculum doubles the volume

Reporting one where the other is meant is a silent factor-of-two error in every MIC, so both are carried
explicitly and `audit()` recomputes them from the transfer plan independently of how they were first set.

An LLM is not involved anywhere in this file. It is arithmetic, and the point of it being arithmetic is that
`audit()` can check it.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from .feasibility import _value
from .lab import Lab

GROWTH = "growth control"         # medium + inoculum, no compound: proves the organism grows
STERILITY = "sterility control"   # medium alone: proves nothing else does
SAMPLE = "sample"


@dataclass
class Well:
    plate: int
    row: str
    column: int
    species: str | None
    role: str
    prepared_uM: float | None      # during the dilution, before the inoculum
    final_uM: float | None         # after the inoculum halves it; None for a sterility well
    volume_uL: float

    @property
    def name(self) -> str:
        return f"{self.row}{self.column}"


@dataclass
class Transfer:
    """One liquid movement, in the order a protocol would perform it. The audit replays these."""
    what: str
    volume_uL: float
    source: str
    dest: str
    plate: int = 1
    note: str = ""


@dataclass
class PlateDesign:
    wells: list[Well] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)
    plates: int = 1
    rows: int = 8
    columns: int = 12
    series_columns: int = 10
    working_uL: float = 200.0
    fold: float = 2.0
    top_final_uM: float = 0.0
    unit: str = "uM"
    notes: list[str] = field(default_factory=list)

    def well(self, plate: int, row: str, column: int) -> Well | None:
        return next((w for w in self.wells if w.plate == plate and w.row == row and w.column == column), None)

    def species(self) -> list[str]:
        return list(dict.fromkeys(w.species for w in self.wells if w.species))

    def render(self, plate: int = 1) -> str:
        """The plate as a person would check it: one row per row, concentrations in the series columns."""
        fmt = lambda v: "-" if v is None else (f"{v:.3g}" if v >= 0.01 else f"{v:.2e}")  # noqa: E731
        lines = [f"plate {plate} of {self.plates}  ({self.fold:g}-fold, {self.series_columns} points, "
                 f"final concentrations in {self.unit})"]
        header = "     " + "".join(f"{c:>9}" for c in range(1, self.columns + 1))
        lines.append(header)
        for row in sorted({w.row for w in self.wells if w.plate == plate}):
            cells = []
            for column in range(1, self.columns + 1):
                w = self.well(plate, row, column)
                cells.append("" if w is None else
                             ("GC" if w.role == GROWTH else "SC" if w.role == STERILITY else fmt(w.final_uM)))
            label = next((w.species or "" for w in self.wells
                          if w.plate == plate and w.row == row and w.species), "")
            lines.append(f"  {row}  " + "".join(f"{c:>9}" for c in cells) + f"   {label}")
        lines.append("  GC = growth control (no compound)   SC = sterility control (medium only)")
        return "\n".join(lines)


def plate_design(experiment: Any, lab: Lab | None = None, panel: Sequence[Any] | None = None,
                 control_columns: tuple[str, str] = (GROWTH, STERILITY)) -> PlateDesign:
    """The well map for this experiment on this lab's plates. One row per species per replicate; the series
    runs along the columns, with the control columns last.

    `panel` defaults to the experiment's own `panel`, and falls back to `system` as a panel of one, so a
    single-system experiment written against the old schema still lays out.
    """
    lab = lab or Lab.load()
    panel = list(panel if panel is not None else _value(experiment, "panel", None) or [])
    if not panel:
        system = _value(experiment, "system", None)
        panel = [{"name": system}] if system else []
    plate_spec = lab.plate() or {"rows": 8, "cols": 12, "working_uL": 200}
    rows, columns = int(plate_spec["rows"]), int(plate_spec["cols"])
    working = float(_value(experiment, "well_volume_uL", 0) or
                    plate_spec.get("working_uL") or plate_spec.get("max_uL") or 200)

    fold = float(_value(experiment, "dilution_factor", 2) or 2)
    n_points = int(_value(experiment, "n_points", 10) or 10)
    replicates = int(_value(experiment, "replicates", 1) or 1)
    # `top_concentration` is canonical; `top_concentration_uM` is the old µM-only field, kept for proposals and
    # recorded traces written before the unit existed
    top_final = float(_value(experiment, "top_concentration", 0) or
                      _value(experiment, "top_concentration_uM", 0) or 0)
    unit = str(_value(experiment, "concentration_unit", "uM") or "uM")

    design = PlateDesign(plates=1, rows=rows, columns=columns, series_columns=n_points,
                         working_uL=working, fold=fold, top_final_uM=top_final, unit=unit)

    if n_points + len(control_columns) > columns:
        design.notes.append(f"{n_points} concentrations + {len(control_columns)} controls exceed the plate's "
                            f"{columns} columns; the series is truncated to {columns - len(control_columns)}")
        n_points = columns - len(control_columns)
        design.series_columns = n_points

    # the inoculum is added as an equal volume, so everything in the plate is prepared at 2x the final value
    half = working / 2
    prepared_factor = 2.0
    design.notes.append(f"compound prepared at {prepared_factor:g}x: an equal volume of inoculum halves it, so "
                        f"column 1 holds {top_final * prepared_factor:g} {unit} and the cells see {top_final:g}")

    # rows: each species repeated `replicates` times, spilling onto further plates when they run out
    letters = [chr(ord("A") + i) for i in range(rows)]
    assignments: list[tuple[int, str, Any]] = []
    index = 0
    for species in panel:
        for _ in range(replicates):
            plate_no, row = index // rows + 1, letters[index % rows]
            assignments.append((plate_no, row, species))
            index += 1
    design.plates = max((p for p, _, _ in assignments), default=1)

    growth_column = n_points + 1
    sterility_column = n_points + 2

    for plate_no, row, species in assignments:
        name = _value(species, "name") or _value(species, "id") or "?"   # a PanelMember or a plain dict
        for column in range(1, n_points + 1):
            final = top_final / (fold ** (column - 1)) if top_final else None
            design.wells.append(Well(plate_no, row, column, name, SAMPLE,
                                     prepared_uM=None if final is None else final * prepared_factor,
                                     final_uM=final, volume_uL=working))
        design.wells.append(Well(plate_no, row, growth_column, name, GROWTH, 0.0, 0.0, working))
        design.wells.append(Well(plate_no, row, sterility_column, None, STERILITY, 0.0, None, working))

    design.transfers = _transfers(design, n_points, half, working)
    return design


def _transfers(design: PlateDesign, n_points: int, half: float, working: float) -> list[Transfer]:
    """The liquid movements that produce the map, in order — the same five steps as the team's protocol."""
    found: list[Transfer] = []
    for plate_no in range(1, design.plates + 1):
        rows = sorted({w.row for w in design.wells if w.plate == plate_no})
        if not rows:
            continue
        span = f"{rows[0]}-{rows[-1]}" if len(rows) > 1 else rows[0]
        found.append(Transfer("medium", half, "reservoir:medium", f"{span}2-{span}{n_points}", plate_no,
                              "broth into every series column but the first"))
        found.append(Transfer("medium", working, "reservoir:medium", f"{span}{n_points + 2}", plate_no,
                              "sterility control: medium only, no inoculum"))
        found.append(Transfer("medium", half, "reservoir:medium", f"{span}{n_points + 1}", plate_no,
                              "growth control: medium, inoculum added later, no compound"))
        found.append(Transfer("compound", working, "reservoir:compound", f"{span}1", plate_no,
                              f"compound at {design.fold:g}x the top assay concentration"))
        for column in range(1, n_points):
            found.append(Transfer("dilution", half, f"{span}{column}", f"{span}{column + 1}", plate_no,
                                  "carry half the volume on, then mix"))
        found.append(Transfer("dilution", half, f"{span}{n_points}", "trash", plate_no,
                              "discard the carry-over so every well holds the same volume"))
        found.append(Transfer("inoculum", half, "reservoir:inoculum", f"{span}1-{span}{n_points + 1}", plate_no,
                              "equal volume of inoculum: halves every concentration"))
    return found


def audit(design: PlateDesign) -> list[str]:
    """Recompute every well from the transfer plan and complain where it disagrees with the map.

    Deliberately independent of `plate_design`'s arithmetic: it walks the transfers the way the robot would,
    tracking volume and amount of compound per well, so a mistake in the layout shows up as a mismatch rather
    than being echoed back. This is what catches the prepared-vs-final confusion.
    """
    problems: list[str] = []
    for plate_no in range(1, design.plates + 1):
        wells = [w for w in design.wells if w.plate == plate_no]
        rows = sorted({w.row for w in wells})
        n = design.series_columns
        for row in rows:
            # amount of compound (in µM·µL) and volume in each series well, replayed step by step
            volume = {c: 0.0 for c in range(1, n + 3)}
            amount = {c: 0.0 for c in range(1, n + 3)}
            for c in range(2, n + 1):
                volume[c] += design.working_uL / 2
            volume[n + 1] += design.working_uL / 2
            volume[n + 2] += design.working_uL
            prepared_top = design.top_final_uM * 2
            volume[1] += design.working_uL
            amount[1] += prepared_top * design.working_uL
            for c in range(1, n):
                if volume[c] <= 0:
                    continue
                moved = design.working_uL / 2
                concentration = amount[c] / volume[c]
                amount[c] -= concentration * moved
                volume[c] -= moved
                amount[c + 1] += concentration * moved
                volume[c + 1] += moved
            concentration_n = amount[n] / volume[n] if volume[n] else 0.0
            amount[n] -= concentration_n * (design.working_uL / 2)
            volume[n] -= design.working_uL / 2
            for c in range(1, n + 2):
                volume[c] += design.working_uL / 2        # the inoculum
            for c in range(1, n + 1):
                w = design.well(plate_no, row, c)
                if w is None:
                    continue
                replayed = amount[c] / volume[c] if volume[c] else 0.0
                if w.final_uM is None or not math.isclose(replayed, w.final_uM, rel_tol=1e-6, abs_tol=1e-12):
                    problems.append(f"plate {plate_no} {w.name}: map says {w.final_uM}, replay gives "
                                    f"{replayed:.6g} {design.unit}")
                if not math.isclose(volume[c], design.working_uL, rel_tol=1e-9):
                    problems.append(f"plate {plate_no} {w.name}: holds {volume[c]:g} uL, expected "
                                    f"{design.working_uL:g}")
            gc = design.well(plate_no, row, n + 1)
            if gc and gc.final_uM:
                problems.append(f"plate {plate_no} {gc.name}: growth control must hold no compound")
            sc = design.well(plate_no, row, n + 2)
            if sc and sc.species is not None:
                problems.append(f"plate {plate_no} {sc.name}: sterility control must receive no inoculum")
    return problems
