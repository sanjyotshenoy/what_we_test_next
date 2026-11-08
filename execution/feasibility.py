"""Can this lab run this experiment? Arithmetic over execution/lab.yaml, never a model's opinion.

    from execution.feasibility import check_feasible
    from execution.lab import Lab
    verdict = check_feasible(experiment, Lab.load(), panel=[{"id": "...", "atmosphere": "anaerobic"}, ...])
    print(verdict.sentence())

The verdict is deliberately not a boolean: a panel that needs three plates is fine, a panel with an obligate
anaerobe in an aerobic-only lab is not, and "drop to duplicate and it fits" is more useful than "no". Every
violation names what is wrong and by how much, so the agent can repair the proposal instead of guessing.

The panel is passed in rather than read off the Experiment because the shared schema does not carry one yet
(TODO(final): take it from Experiment.panel once that lands). Each entry is {id, name?, atmosphere?} - the
growth requirements come from whoever assembled the panel, not from here.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .lab import Lab

DEFAULT_CONTROL_COLUMNS = 2      # growth control + sterility control, as in the team's MIC protocol


@dataclass
class Verdict:
    feasible: bool
    violations: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    plates_needed: int = 0
    rows_needed: int = 0
    columns_needed: int = 0
    tip_columns_needed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    def sentence(self) -> str:
        head = (f"Runnable on {self.plates_needed} plate(s)." if self.feasible
                else f"Not runnable as proposed: {len(self.violations)} problem(s).")
        parts = [head]
        parts += [f"  - {v}" for v in self.violations]
        if self.suggestions:
            parts.append("  suggestions:")
            parts += [f"    * {s}" for s in self.suggestions]
        if self.warnings:
            parts += [f"  ! {w}" for w in self.warnings]
        return "\n".join(parts)


def _value(experiment: Any, name: str, default=None):
    """Read a field off an Experiment model or a plain dict, so callers can pass either."""
    if isinstance(experiment, dict):
        return experiment.get(name, default)
    return getattr(experiment, name, default)


def _series_volumes(experiment: Any) -> tuple[float, float]:
    """(volume held per well, volume carried column to column). The MIC protocol's 100 + 100 format: each well
    holds `working`, half of which is carried on and half replaced by inoculum."""
    working = float(_value(experiment, "well_volume_uL", 200) or 200)
    return working, working / 2


def check_feasible(experiment: Any, lab: Lab | None = None, panel: Sequence[dict] | None = None,
                   control_columns: int = DEFAULT_CONTROL_COLUMNS) -> Verdict:
    """Whether `lab` can run `experiment` against `panel`, with every limit checked explicitly."""
    lab = lab or Lab.load()
    panel = list(panel or [])
    v = Verdict(feasible=True)
    v.warnings.extend(lab.unconfirmed())

    n_points = int(_value(experiment, "n_points", 0) or 0)
    replicates = int(_value(experiment, "replicates", 1) or 1)
    well_uL, carry_uL = _series_volumes(experiment)

    # --- the conditions the panel needs -----------------------------------------------------------------
    have = lab.atmospheres()
    # a species may name one atmosphere, several, or "facultative" (grows either way); it is runnable if any of
    # the ones it will tolerate is available. Checked in both directions: an obligate aerobe such as
    # P. aeruginosa is as unrunnable in an anaerobic-only setup as B. fragilis is in air.
    for species in panel:
        wanted = species.get("atmosphere", "aerobic")
        wanted = [wanted] if isinstance(wanted, str) else list(wanted)
        if any(str(w).startswith("facult") for w in wanted):
            continue
        tolerates = {str(w) for w in wanted}
        if not (tolerates & have):
            name = species.get("name") or species.get("id", "?")
            v.violations.append(f"{name} needs {'/'.join(sorted(tolerates))} incubation; this lab has "
                                f"{'/'.join(sorted(have)) or 'nothing specified'}")
    if any("incubation" in x for x in v.violations):
        v.suggestions.append("drop the species that do not fit the available atmosphere, or run them by hand "
                             "(anaerobes: CLSI M11 agar dilution) and flag them for a person")
    temperature = _value(experiment, "incubation_C")
    if temperature is not None and not lab.can_incubate_at(temperature):
        v.violations.append(f"incubation at {temperature} C is not available "
                            f"(have: {lab.capabilities.get('incubation_C')})")

    # --- does it fit on the plates we have? --------------------------------------------------------------
    plate = lab.plate()
    if plate is None:
        v.violations.append("no well plate on hand")
    elif panel and n_points:
        rows, cols = int(plate["rows"]), int(plate["cols"])
        v.columns_needed = n_points + control_columns
        v.rows_needed = len(panel) * replicates
        if v.columns_needed > cols:
            v.violations.append(f"{n_points} concentrations + {control_columns} control columns = "
                                f"{v.columns_needed} columns, more than the plate's {cols}")
            v.suggestions.append(f"use {cols - control_columns} concentrations, or split the series over two plates")
        rows_per_plate = rows
        v.plates_needed = math.ceil(v.rows_needed / rows_per_plate) if rows_per_plate else 0
        on_hand = int(plate.get("count", 0))
        if v.plates_needed > on_hand:
            v.violations.append(f"{len(panel)} species x {replicates} replicates = {v.rows_needed} rows = "
                                f"{v.plates_needed} plates, more than the {on_hand} on hand")
        if v.plates_needed > 1:
            fits = rows_per_plate // max(1, replicates)
            v.suggestions.append(f"{v.rows_needed} rows needs {v.plates_needed} plates; "
                                 f"{fits} species would fit on one at n={replicates}")
        if well_uL > float(plate.get("working_uL", plate.get("max_uL", 0))):
            v.violations.append(f"{well_uL:g} uL per well is over the plate's working volume "
                                f"{plate.get('working_uL')} uL")

    # --- can the pipettes move these volumes? -------------------------------------------------------------
    for label, volume in (("the column-to-column transfer", carry_uL), ("the well fill", well_uL / 2)):
        if volume and lab.pipette_for(volume) is None:
            confirmed = ", ".join(f"{p['model']} {p['min_uL']}-{p['max_uL']} uL" for p in lab.pipettes()) or "none"
            v.violations.append(f"{label} is {volume:g} uL, outside every confirmed pipette ({confirmed})")

    # --- tips --------------------------------------------------------------------------------------------
    if panel and n_points:
        # the series can share one tip column per plate; the inoculum needs a fresh one per column
        v.tip_columns_needed = v.plates_needed * (1 + v.columns_needed)
        available = lab.tip_columns()
        if v.tip_columns_needed > available:
            v.violations.append(f"needs {v.tip_columns_needed} columns of tips, {available} on hand")
            v.suggestions.append("load another tip rack, or run the plates in separate sessions")

    # --- reagent volumes ----------------------------------------------------------------------------------
    usable = lab.reservoir_usable_mL()
    if panel and n_points and usable:
        channels = 8
        broth_mL = (v.plates_needed * v.columns_needed * channels * well_uL / 2) / 1000
        if broth_mL > usable:
            v.violations.append(f"needs about {broth_mL:.1f} mL of medium per reservoir channel, "
                                f"usable capacity is {usable:.1f} mL")
            v.suggestions.append("split the medium across two reservoir channels, or refill between plates")
        v.detail["medium_mL"] = round(broth_mL, 1)

    # --- can we read it? -----------------------------------------------------------------------------------
    readout = str(_value(experiment, "readout", "") or "").lower()
    modes = lab.read_modes()
    wanted = ("absorbance" if any(w in readout for w in ("turbidity", "od", "absorbance", "growth")) else
              "luminescence" if "lumin" in readout else
              "fluorescence" if "fluor" in readout else None)
    if wanted and wanted not in modes:
        v.violations.append(f"readout '{readout}' needs {wanted}, which no reader here has ({sorted(modes)})")
    elif wanted is None and readout:
        v.warnings.append(f"could not tell which reader mode '{readout}' needs; check by hand")

    v.feasible = not v.violations
    return v


def feasible_panel_size(lab: Lab | None = None, replicates: int = 3, plates: int = 1) -> int:
    """How many species fit, at this replication, on this many plates. The trade-off the agent has to make."""
    lab = lab or Lab.load()
    plate = lab.plate()
    return (int(plate["rows"]) * plates) // max(1, replicates) if plate else 0


def describe(panel: Iterable[dict]) -> str:
    return ", ".join(s.get("name") or s.get("id", "?") for s in panel)
