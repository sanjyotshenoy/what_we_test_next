"""How a template parameter's *default* value is chosen from its observations.

A curated template (`templates/*.json`) records, for every parameter, each value seen across the exemplar
assays, with the AID (or file) and a verbatim quote. None of those observations is marked as the default. This
module picks one and writes down why, so no number in the graph appears without a reason.

Four rules, in this order:

1. **Reference run** for the parameters that describe *one* concentration series (`SERIES_PARAMETERS`, or any
   parameter the template marks `"series": true`). Aggregating them independently can assemble a series nobody
   ever ran - one assay's top concentration with another's spacing need not span what it should - so all of them
   come from a single exemplar: the candidate (an exemplar that reports *every* series parameter) whose series
   sits closest to the centre of all exemplars. Distance is per parameter |log10(v / centre)| for multiplicative
   quantities (concentrations, fold-spacings) and |v - centre| for counts, each divided by that parameter's own
   median absolute deviation so one parameter cannot dominate, then summed.
2. **Nearest to centre** for every other numeric parameter (volumes, times, temperatures, counts, ...): the
   observation closest to the centre of that parameter's observations. The default is always a value some
   exemplar really used; a mean or a median that nobody ran is never written out.
3. **Modal value** when a parameter has non-numeric observations ("room temperature", "overnight"): the value
   the most exemplars state verbatim. Nothing is averaged.
4. **Canonical snapping** for spacing-like parameters: a chosen fold-step within `SNAP_TOLERANCE` of a member of
   `CANONICAL_SPACINGS` is snapped to it and the snap is recorded (2.97-fold is a rounding artefact of reading
   concentration columns; 3-fold is what a pipette can do). Outside the tolerance the observed value is kept and
   flagged `off_ladder` rather than forced.

The centre is the **geometric median** for multiplicative quantities (in 1-D: the median of the logs) and the
ordinary median for linear ones. A parameter whose exemplars disagree widely - at least a decade of spread on a
log-scale parameter, a spread wider than the centre itself on a linear one, or a chosen value far from the
centre - carries `exemplars_disagree: true` and says so in its derivation text, so a reader sees a genuine
disagreement instead of a confident single number.

A parameter with observations but no resolvable default raises `DefaultError`: it is never silently resolved to
the first observation.

    from kg.protocols.defaults import resolve_parameters
    props = resolve_parameters(template)          # {parameter name: the Parameter node's props}
"""
import math
import statistics
from collections import Counter

# The parameters that describe one concentration series and must therefore come from one exemplar assay. A
# template can add to this list per parameter with `"series": true`.
SERIES_PARAMETERS = ("top_concentration", "bottom_concentration", "dilution_factor", "n_points")

# Pipettable serial-dilution steps: 2-fold, 2.5, 3, half-log (3.162), 4, 5, 10. A chosen spacing within
# SNAP_TOLERANCE (relative) of one of these is snapped to it.
CANONICAL_SPACINGS = (2.0, 2.5, 3.0, math.sqrt(10), 4.0, 5.0, 10.0)
SNAP_TOLERANCE = 0.05

# Names that are a fold-spacing whatever their unit says: log-scale, and snappable.
SPACING_NAMES = ("dilution_factor", "fold_dilution", "dilution_step", "spacing")

# unit (as written) -> (dimension, factor to the canonical unit, canonical unit, scale). Case-sensitive first,
# because "nM" (nanomolar) and "nm" (nanometre) are different dimensions. Concentrations and fold-spacings are
# multiplicative, so their distances are measured in decades; everything else is linear.
_DIMENSIONS = {
    "concentration": ({"M": 1e6, "mM": 1e3, "uM": 1.0, "µM": 1.0, "nM": 1e-3, "pM": 1e-6}, "uM", "log"),
    "cell_density": ({"CFU/mL": 1.0, "CFU/ml": 1.0, "cfu/ml": 1.0}, "CFU/mL", "log"),
    "spacing": ({"fold": 1.0, "-fold": 1.0, "x": 1.0}, "fold", "log"),
    "time": ({"s": 1 / 60, "sec": 1 / 60, "min": 1.0, "minute": 1.0, "minutes": 1.0,
              "h": 60.0, "hr": 60.0, "hrs": 60.0, "hour": 60.0, "hours": 60.0, "d": 1440.0}, "min", "linear"),
    "volume": ({"nL": 1e-3, "uL": 1.0, "µL": 1.0, "mL": 1e3, "L": 1e6}, "uL", "linear"),
    "temperature": ({"C": 1.0, "degrees C": 1.0, "celsius": 1.0}, "C", "linear"),
    "wavelength": ({"nm": 1.0}, "nm", "linear"),
    "fraction": ({"%": 1.0}, "%", "linear"),
}

# A chosen value this far from the centre, or exemplars spread this widely, mean the exemplars genuinely
# disagree and a single default is misleading. Decades for log-scale parameters; multiples of the centre for
# linear ones.
WIDE_SPREAD_DECADES = 1.0
WIDE_SPREAD_RATIO = 1.0
FAR_FROM_CENTRE_DECADES = 0.5
FAR_FROM_CENTRE_RATIO = 1.0

TIES = 1e-9          # distances closer than this are a tie, broken by frequency then exemplar order

# The flags that mean "the exemplars genuinely disagree": a human should look at `observed` rather than trust
# one default. `off_ladder` and `no_reference_run` are about the derivation, not the disagreement.
DISAGREEMENT_FLAGS = frozenset({"wide_spread", "chosen_far_from_centre", "mixed_value_kinds", "no_majority"})


class DefaultError(ValueError):
    """A parameter has observations but no default can be derived from them (never resolve to observed[0])."""


def _dimension(unit: str | None) -> tuple[str, float, str, str]:
    """(dimension, factor to the canonical unit, canonical unit, "log"|"linear") for a unit as written. An
    unknown unit is its own dimension with factor 1, so counts ("wells", "concentrations", "runs") and anything
    we have not seen compare in whatever unit the template wrote."""
    if unit is None:
        return ("dimensionless", 1.0, None, "linear")
    for name, (units, canonical, scale) in _DIMENSIONS.items():
        if unit in units:
            return (name, units[unit], canonical, scale)
    matches = [(name, units, canonical, scale) for name, (units, canonical, scale) in _DIMENSIONS.items()
               if unit.strip().lower() in {u.lower() for u in units}]
    if len(matches) == 1:                               # unambiguous apart from case
        name, units, canonical, scale = matches[0]
        factor = next(f for u, f in units.items() if u.lower() == unit.strip().lower())
        return (name, factor, canonical, scale)
    return (f"count:{unit}", 1.0, unit, "linear")


def exemplar_of(observation: dict) -> str | None:
    """The exemplar an observation was read from: `aid:<n>` for a PubChem AID, `file:<path>` for one of our own
    protocol files. None when the observation names neither (which is an error for a default)."""
    if observation.get("aid") is not None:
        return f"aid:{observation['aid']}"
    if observation.get("file"):
        return f"file:{observation['file']}"
    return None


def is_series(name: str, parameter: dict) -> bool:
    return name in SERIES_PARAMETERS or bool(parameter.get("series"))


def is_spacing(name: str, parameter: dict) -> bool:
    unit = parameter.get("unit") or next((o.get("unit") for o in parameter.get("observed", []) if o.get("unit")),
                                         None)
    return any(name == s or name.endswith(f"_{s}") for s in SPACING_NAMES) or unit in _DIMENSIONS["spacing"][0]


def centre_of(values: list[float], scale: str) -> float:
    """The centre of a parameter's observations: the geometric median for multiplicative quantities (in one
    dimension, the median of the logs), the ordinary median for linear ones."""
    if not values:
        raise DefaultError("no values to take a centre of")
    if scale == "log":
        if any(v <= 0 for v in values):
            raise DefaultError(f"log-scale parameter with a non-positive value: {values}")
        return 10 ** statistics.median([math.log10(v) for v in values])
    return float(statistics.median(values))


def distance(value: float, centre: float, scale: str) -> float:
    """How far one observation sits from the centre: decades for log-scale quantities, absolute for linear."""
    if scale == "log":
        return abs(math.log10(value) - math.log10(centre))
    return abs(value - centre)


def snap(value: float, ladder: tuple[float, ...] = CANONICAL_SPACINGS,
         tolerance: float = SNAP_TOLERANCE) -> tuple[float, float | None]:
    """(value to use, the ladder step it was snapped to or None). Nearest member of `ladder` within `tolerance`
    relative, else the value unchanged."""
    nearest = min(ladder, key=lambda step: abs(math.log10(value / step)))
    return (nearest, nearest) if abs(value - nearest) / nearest <= tolerance else (value, None)


def _number(observation: dict, factor: float) -> float | None:
    value = observation.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) * factor


def _format(value) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    if float(value) == int(value):
        return str(int(value))
    return f"{value:.4g}"


def _with_unit(value, unit: str | None) -> str:
    return f"{_format(value)} {unit}" if unit else _format(value)


class _Observations:
    """One parameter's observations, normalized to a single unit so they can be compared."""

    def __init__(self, name: str, parameter: dict, order: dict[str, int]):
        self.name = name
        self.parameter = parameter
        self.observed = parameter.get("observed") or []
        if not self.observed:
            raise DefaultError(f"parameter {name!r} has no observations: nothing to derive a default from")
        self.order = order
        self.rows = []
        for i, observation in enumerate(self.observed):
            exemplar = exemplar_of(observation)
            if exemplar is None:
                raise DefaultError(f"parameter {name!r}: observation {i} names neither an AID nor a file")
            dimension, factor, canonical, scale = _dimension(observation.get("unit"))
            self.rows.append({"index": i, "exemplar": exemplar, "observation": observation,
                              "dimension": dimension, "canonical": canonical, "scale": scale,
                              "factor": factor, "number": _number(observation, factor),
                              "rank": order.get(exemplar, len(order) + i)})
        self.numeric = [r for r in self.rows if r["number"] is not None]
        self.spacing = is_spacing(name, parameter)
        dimensions = {r["dimension"] for r in self.numeric}
        if len(dimensions) > 1:
            raise DefaultError(f"parameter {name!r}: observations mix dimensions {sorted(dimensions)}; "
                               f"no common unit to compare them in")
        self.dimension = next(iter(dimensions), None)
        self.canonical_unit = self.numeric[0]["canonical"] if self.numeric else None
        self.scale = "log" if self.spacing else (self.numeric[0]["scale"] if self.numeric else "linear")
        self.mixed = bool(self.numeric) and len(self.numeric) < len(self.rows)
        # Any observation stated in words ("room temperature", "overnight") makes the whole parameter
        # categorical: the modal rule then counts verbatim values, because the words cannot be ordered against
        # the numbers without inventing a conversion.
        self.categorical = not self.numeric or self.mixed

    @property
    def values(self) -> list[float]:
        return [r["number"] for r in self.numeric]

    def centre(self) -> float:
        return centre_of(self.values, self.scale)

    def deviations(self) -> dict[str, float]:
        """exemplar -> how far its (first) observation sits from the centre."""
        centre = self.centre()
        found = {}
        for row in self.numeric:
            found.setdefault(row["exemplar"], distance(row["number"], centre, self.scale))
        return found

    def mad(self) -> float | None:
        """The median absolute deviation from the centre: the per-parameter scale that keeps one parameter from
        dominating a summed distance. None when every exemplar agrees (the parameter cannot discriminate)."""
        deviations = sorted(self.deviations().values())
        if not deviations:
            return None
        for candidate in (statistics.median(deviations), sum(deviations) / len(deviations)):
            if candidate > 0:
                return candidate
        return None

    def row_for(self, exemplar: str) -> dict | None:
        return next((r for r in self.numeric if r["exemplar"] == exemplar), None)

    def nearest(self) -> dict:
        """The observation closest to the centre; ties go to the most frequently observed value, then to the
        exemplar the template lists first."""
        centre = self.centre()
        counts = Counter(r["number"] for r in self.numeric)
        return min(self.numeric, key=lambda r: (round(distance(r["number"], centre, self.scale) / TIES),
                                                -counts[r["number"]], r["rank"]))

    def spread(self) -> dict:
        values = self.values
        low, high = min(values), max(values)
        found = {"min": low, "max": high, "unit": self.canonical_unit, "n_values": len(set(values))}
        if self.scale == "log" and low > 0:
            found["decades"] = round(math.log10(high / low), 3)
        else:
            found["range"] = high - low
        return found


def _flags(observations: _Observations, chosen: dict, centre: float, show) -> tuple[list[str], str]:
    """The dispersion flags for a numeric parameter, and the sentence that explains them."""
    flags, said = [], []
    spread = observations.spread()
    low, high = show(spread["min"]), show(spread["max"])
    if observations.scale == "log":
        wide = spread.get("decades", 0.0) >= WIDE_SPREAD_DECADES
        how = f"a {spread['max'] / spread['min']:.3g}x spread, {low} to {high}"
    else:
        wide = centre > 0 and spread["range"] > WIDE_SPREAD_RATIO * abs(centre)
        how = f"{low} to {high}, a spread wider than the centre itself"
    if wide:
        flags.append("wide_spread")
        said.append(f"the exemplars disagree widely ({how}), so a single default is misleading: use `observed`")
    far = distance(chosen["number"], centre, observations.scale) > (
        FAR_FROM_CENTRE_DECADES if observations.scale == "log" else FAR_FROM_CENTRE_RATIO * abs(centre))
    if far:
        flags.append("chosen_far_from_centre")
        said.append(f"the chosen exemplar sits far from the centre ({show(centre)})")
    return flags, "; ".join(said)


def _base(observations: _Observations, chosen: dict) -> dict:
    """The props every default carries: the value, where it came from, and all the observations."""
    observation = chosen["observation"]
    props = {
        "value": observation["value"], "unit": observation.get("unit") or observations.parameter.get("unit"),
        "aid": observation.get("aid"), "quote": observation.get("quote"),
        "observed": observations.observed, "n_exemplars": len(observations.observed),
        "n_exemplars_reporting": len({r["exemplar"] for r in observations.rows}),
        "from_exemplar": chosen["exemplar"], "series_parameter": is_series(observations.name,
                                                                          observations.parameter),
    }
    if observation.get("file"):
        props["file"] = observation["file"]
    return props


def _categorical(observations: _Observations) -> dict:
    """A parameter with non-numeric observations ("room temperature"): the value the most exemplars state."""
    counts = Counter(str(r["observation"].get("value")) for r in observations.rows)
    best, support = counts.most_common(1)[0]
    chosen = min((r for r in observations.rows if str(r["observation"].get("value")) == best),
                 key=lambda r: r["rank"])
    props = _base(observations, chosen)
    n = len(observations.rows)
    flags = ["mixed_value_kinds"] if observations.mixed else []
    disagree = len(counts) > 1 and support * 2 <= n      # no value is stated by MORE than half the exemplars
    if disagree:
        flags.append("no_majority")
    others = sorted({_with_unit(r["observation"].get("value"), r["observation"].get("unit"))
                     for r in observations.rows if str(r["observation"].get("value")) != best})
    derivation = (f"modal value: {support} of {n} observations state "
                  f"{_with_unit(chosen['observation'].get('value'), props['unit'])} verbatim, from "
                  f"{chosen['exemplar']}; non-numeric values cannot be averaged or ordered")
    if others:
        derivation += f". Other exemplars say: {', '.join(others)}"
    if disagree:
        derivation += (". No value is stated by more than half the observations, so this default is a "
                       "coin-flip among them")
    if props["series_parameter"]:
        # a series parameter nobody states as a number cannot take part in a reference run
        flags.append("no_reference_run")
        derivation += (". Stated in words, so it is left out of the series' reference run: mutual consistency "
                       "with the other series parameters is NOT guaranteed")
    props.update({"default_rule": "modal value", "derivation": derivation, "scale": "categorical",
                  "centre": None, "centre_unit": None, "centre_rule": None,
                  "normalized_value": None, "normalized_unit": None,
                  "snapped": False, "snapped_from": None, "snapped_to": None, "canonical_ladder": None,
                  "spread": {"values": sorted(counts), "n_values": len(counts)},
                  "exemplars_disagree": bool(set(flags) & DISAGREEMENT_FLAGS), "flags": flags})
    return props


def _numeric(observations: _Observations, chosen: dict, rule: str, why: str,
             reference: str | None = None) -> dict:
    """Finish a numeric default: snapping, the derivation sentence, the dispersion flags."""
    centre = observations.centre()
    props = _base(observations, chosen)
    value, unit = chosen["observation"]["value"], props["unit"]
    normalized = chosen["number"]
    snapped_to = None
    if observations.spacing:
        snapped, snapped_to = snap(float(normalized))
        if snapped_to is not None and snapped != normalized:
            value, normalized = snapped, snapped
    # Numbers in the derivation text are shown in the chosen observation's own unit (5 nM, not 0.005 uM), while
    # `centre` and `spread` in the props stay in the canonical unit a reader can compare across exemplars.
    factor = chosen["factor"] or 1.0
    show = (lambda canonical: _with_unit(canonical / factor, unit))
    flags, dispersion = _flags(observations, chosen, centre, show)
    spread = observations.spread()
    centre_rule = "geometric median" if observations.scale == "log" else "median"
    n = len({r["exemplar"] for r in observations.numeric})
    sentence = f"{rule}: {why}"
    if len(observations.numeric) > 1:
        sentence += (f". Centre of {len(observations.numeric)} observations from {n} exemplars = "
                     f"{show(centre)} ({centre_rule}, {show(spread['min'])} to {show(spread['max'])})")
    else:
        sentence += ". One observation, so it is also the centre: nothing to compare it against"
    if observations.spacing:
        observed_value = chosen["observation"]["value"]
        if snapped_to is not None and value != observed_value:
            off = abs(float(observed_value) - snapped_to) / snapped_to
            sentence += (f". Snapped {_with_unit(observed_value, unit)} to the canonical {_format(snapped_to)}-"
                         f"fold step ({off * 100:.1f}% away, within the {SNAP_TOLERANCE:.0%} tolerance): a "
                         f"{_format(observed_value)}-fold transfer is a reading artefact, not a pipetting step")
        elif snapped_to is None:
            flags.append("off_ladder")
            ladder = ", ".join(_format(s) for s in CANONICAL_SPACINGS)
            sentence += (f". Kept as observed: no canonical step ({ladder}) is within {SNAP_TOLERANCE:.0%}, so "
                         f"the value is flagged rather than forced onto the ladder")
    if dispersion:
        sentence += f". Warning: {dispersion}"
    was_snapped = snapped_to is not None and value != chosen["observation"]["value"]
    props.update({
        "value": value, "normalized_value": normalized, "normalized_unit": spread["unit"],
        "default_rule": rule, "derivation": sentence, "scale": observations.scale,
        "centre": round(centre, 6), "centre_unit": spread["unit"], "centre_rule": centre_rule, "spread": spread,
        "snapped": was_snapped,
        "snapped_from": chosen["observation"]["value"] if was_snapped else None,
        "snapped_to": snapped_to if was_snapped else None,
        "canonical_ladder": [round(s, 4) for s in CANONICAL_SPACINGS] if observations.spacing else None,
        "exemplars_disagree": bool(set(flags) & DISAGREEMENT_FLAGS),
        "flags": flags,
    })
    if reference:
        props["reference_exemplar"] = reference
    return props


def _reference_run(series: dict[str, _Observations]) -> tuple[str | None, dict[str, float], list[str]]:
    """The exemplar all series parameters should come from: the candidate (an exemplar reporting every series
    parameter) whose series sits closest to the centre of all exemplars. Returns (exemplar, total normalized
    distance per candidate, the parameter names that were summed)."""
    reporting = [set(o.deviations()) for o in series.values()]
    candidates = set.intersection(*reporting) if reporting else set()
    if not candidates:
        return None, {}, []
    scales = {name: o.mad() for name, o in series.items()}
    used = sorted(name for name, scale in scales.items() if scale)
    totals = {candidate: sum(series[name].deviations()[candidate] / scales[name] for name in used)
              for candidate in candidates}
    ranks = {candidate: min(o.row_for(candidate)["rank"] for o in series.values() if o.row_for(candidate))
             for candidate in candidates}
    best = min(candidates, key=lambda c: (round(totals[c] / TIES), ranks[c]))
    return best, {c: round(t, 4) for c, t in totals.items()}, used


def resolve_parameters(template: dict) -> dict[str, dict]:
    """{parameter name: the Parameter node's props}, each default carrying its derivation. Raises DefaultError
    if a parameter has observations but no default can be derived from them."""
    order = {}
    for i, exemplar in enumerate(template.get("exemplars", [])):
        key = exemplar_of(exemplar)
        if key is not None:
            order[key] = i
    parameters = template["parameters"]
    observations = {name: _Observations(name, parameter, order) for name, parameter in parameters.items()}

    series = {name: o for name, o in observations.items()
              if is_series(name, parameters[name]) and not o.categorical}
    reference, totals, summed = _reference_run(series) if series else (None, {}, [])

    resolved = {}
    for name, o in observations.items():
        if o.categorical:
            resolved[name] = _categorical(o)
            continue
        if name in series and reference is not None:
            chosen = o.row_for(reference)
            rivals = ", ".join(f"{c} {t:g}" for c, t in sorted(totals.items()) if c != reference)
            mine = _with_unit(chosen["observation"]["value"], chosen["observation"].get("unit"))
            tied = sorted(c for c, t in totals.items()
                          if c != reference and abs(t - totals[reference]) < TIES)
            standing = (f"of the {len(totals)} exemplars reporting the whole series its own series sits closest "
                        f"to the centre, total normalized distance {totals[reference]:g} over "
                        f"{', '.join(summed)} (vs {rivals})") if rivals else \
                       (f"the only exemplar reporting all of {', '.join(sorted(series))}")
            if tied:
                standing += (f"; it ties with {', '.join(tied)} and wins on the order the template lists its "
                             f"exemplars")
            why = (f"all of {', '.join(sorted(series))} come from one exemplar, {reference}: {standing}. Its "
                   f"value here is {mine}")
            props = _numeric(o, chosen, "reference run", why, reference=reference)
            props["reference_run_candidates"] = totals
            props["reference_run_parameters"] = sorted(series)
            resolved[name] = props
            continue
        if name in series and reference is None:
            chosen = o.nearest()
            why = ("no exemplar reports every series parameter, so this one falls back to the nearest "
                   "observation: mutual consistency with the other series parameters is NOT guaranteed")
            props = _numeric(o, chosen, "nearest to centre", why)
            props["flags"] = [*props["flags"], "no_reference_run"]
            props["exemplars_disagree"] = True
            resolved[name] = props
            continue
        chosen = o.nearest()
        if len(o.numeric) == 1:
            why = (f"only one exemplar reports it, "
                   f"{_with_unit(chosen['observation']['value'], chosen['observation'].get('unit'))} from "
                   f"{chosen['exemplar']}")
            resolved[name] = _numeric(o, chosen, "only observation", why)
            continue
        why = (f"{chosen['exemplar']}'s "
               f"{_with_unit(chosen['observation']['value'], chosen['observation'].get('unit'))} is the observed "
               f"value closest to the centre")
        resolved[name] = _numeric(o, chosen, "nearest to centre", why)

    for name, props in resolved.items():
        if props.get("value") is None or not props.get("derivation"):
            raise DefaultError(f"parameter {name!r}: no default could be derived")
    return resolved
