"""Where to centre the concentration series: the one number the protocol template cannot give.

A dose-response design needs two things that live in different graphs. The **protocol template** knows the
*shape* of a good assay (how many concentrations, what spacing, which controls) — generic across compounds,
every value citing a PubChem AID. The **biology graph** knows the *scale* for this compound: the measured
potencies of its structural analogs (`bio_kg_analogs`). Deciding where to put the top concentration is the
join between them, and it was being done implicitly by the LLM in prose — the single number that most
determines whether the experiment works was the only one with no provenance and no check.

This module does that join deterministically and records the derivation:

    from agent.anchor import Shape, anchor_from_result, check_series_consistent_with_analogs

    analogs = kb.bio_kg_analogs("CHEMBL5593141", "BTK", k=3)
    shape = Shape.from_template(kb.protocol_kg_templates("potency", target="BTK")["templates"][0])
    anchor = anchor_from_result(analogs, shape)
    anchor.top_concentration_uM        # 0.638 µM, against the template's default 12 µM
    anchor.derivation                  # analogs used, statistic, multiplier, the resulting bounds

The anchor is a **default with justification allowed**, not a constraint: `propose.py` tells the model it may
depart with a stated reason, and the trace records which it did. A wrong anchor must not be systematised.

## The multiplier, and what the AGM does and does not say

The series is centred on the analogs' median potency: with the template's own spacing `f` and point count `n`,
the top concentration is

    top = median_analog_IC50 * f ** ((n - 1) / 2)

so half the points sit above the expected IC50 and half below. That *centring* is AGM-grounded — it is the same
sentence `rule:agm/bracket_expected_ic50` already quotes ("Ideally, half the data points on the IC50 curve are
above the IC50 value and half are below the IC50 value, including a minimum and maximum signal.", Basics of
Enzymatic Assays for HTS, NBK92007) — and the multiplier is *derived* from it plus the template's shape rather
than asserted: 2.97**4 = 78x for the kinase template's 9-point 2.97-fold series, 3**4.5 = 140x for a 10-point
3-fold one, i.e. the same order as the common "top = 100x the expected IC50" rule of thumb.

TODO(final): the chapters cited in kg/protocols/rules.yaml (NBK92007, NBK83783, NBK91991, NBK91994, NBK91992,
NBK464633, NBK374281) were searched for a numeric top-concentration multiplier and give none — they state the
centring and the plateaus qualitatively ("It is important to use enough inhibitor concentrations to provide
well-defined top and bottom plateau values.", NBK92007). So `FALLBACK_MULTIPLIER` below (used only when the
template gives no shape) is a **documented heuristic, not an AGM number**, and no AGM citation is attached to
it. Do not invent one.

## Why an unweighted median

The statistic is an **unweighted** median of the usable analog potencies. Weighting by Tanimoto similarity was
considered and rejected, for reasons that are about this data rather than about the idea: the analogs come back
k=3 at a time within a narrow similarity band (0.578-0.597 for the demo compound), so any weighting is within
rounding of uniform; a weighted median over two or three points is a step function of the weights, so it is
neither smooth nor easy for a reviewer to re-derive by hand; and similarity-to-potency is not calibrated
anywhere in this repo, so a weight would be a second invented number on top of the multiplier. The
similarities are recorded in the derivation, so a later version can weight and show the difference.
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

__all__ = ["Shape", "Anchor", "Check", "DEFAULT_SHAPE", "FALLBACK_MULTIPLIER", "WIDE_SPREAD_LOG10",
           "TOLERANCE_STEPS", "anchor_from_analogs", "anchor_from_result", "series_from",
           "check_series_consistent_with_analogs"]

# Only used when no template shape is available (the model asked for the anchor before fetching a template).
# A heuristic, NOT an AGM number - see the module docstring. TODO(final): heuristic multiplier.
FALLBACK_MULTIPLIER = 100.0

# More than this many orders of magnitude between the analogs' potencies and the median is a weak summary of
# them: the anchor still fires (a number is better than prose) but is flagged low confidence.
WIDE_SPREAD_LOG10 = 3.0

# How far a proposed top concentration may sit from the anchor before it counts as ignoring the analogs,
# in dilution steps of the series' own spacing. One step = the resolution the series itself has.
TOLERANCE_STEPS = 1.0

AGM = {"rule": "rule:agm/bracket_expected_ic50", "chapter": "Basics of Enzymatic Assays for HTS",
       "nbk": "NBK92007",
       "quote": "Ideally, half the data points on the IC50 curve are above the IC50 value and half are below "
                "the IC50 value, including a minimum and maximum signal."}

_CENSORED = re.compile(r"^\s*[<>~]|^\s*(?:ge|le|gt|lt)\b", re.I)


def _sig(x: float, digits: int = 3) -> float:
    """`x` to `digits` significant figures: a concentration a lab can actually set."""
    if x == 0 or not math.isfinite(x):
        return float(x)
    return float(round(x, -int(math.floor(math.log10(abs(x)))) + (digits - 1)))


@dataclass
class Shape:
    """The *shape* of the series, from a protocol template: spacing, point count, and the template's own
    default top concentration (what the agent falls back to when the anchor cannot fire)."""
    dilution_factor: float
    n_points: int
    top_concentration_uM: float | None = None
    source: str = ""          # e.g. the protocol ID the shape came from

    @classmethod
    def from_template(cls, template: dict | None) -> "Shape | None":
        """The shape held by one template detail from `protocol_kg_templates` (`templates[i]`), whose `params`
        carry the curated defaults with their AID and quote. None when the template has no series parameters
        (the five archetype-only protocols have none)."""
        params = (template or {}).get("params") or {}

        def value(name):
            p = params.get(name) or {}
            v = p.get("value")
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        factor, points, top = value("dilution_factor"), value("n_points"), value("top_concentration")
        if not factor or not points:
            return None
        return cls(dilution_factor=float(factor), n_points=int(points), top_concentration_uM=top,
                   source=str((template or {}).get("id") or ""))


# Spacing and point count when no template shape is in hand: 3-fold steps (rule:agm/even_spacing) and 10
# concentrations (rule:agm/min_points_enzyme_ic50), both AGM-quoted in kg/protocols/rules.yaml. The nominal
# 10 µM top is only the "template default" the anchor is compared against until a real template arrives.
# TODO(final): placeholder top; the template's own curated default replaces it as soon as it is fetched.
DEFAULT_SHAPE = Shape(dilution_factor=3.0, n_points=10, top_concentration_uM=10.0, source="agm defaults")


def series_from(top_uM: float, dilution_factor: float, n_points: int) -> list[float]:
    """The concentration series, highest first, as a lab would pipette it."""
    return [_sig(top_uM / dilution_factor ** i, 3) for i in range(int(n_points))]


def _value(analog: dict) -> tuple[float | None, str]:
    """(potency in nM, why it was skipped). Censored ('>128'), missing, zero and unparseable values are
    skipped and counted rather than silently coerced."""
    relation = str(analog.get("relation") or analog.get("standard_relation") or "").strip()
    if analog.get("censored") or (relation and relation not in ("=", "==")):
        return None, f"censored (relation {relation or 'censored'})"
    raw = analog.get("ic50_nM", analog.get("ic50_nm"))
    if raw is None or raw == "":
        return None, "no IC50 value"
    if isinstance(raw, str):
        if _CENSORED.match(raw):
            return None, f"censored value {raw.strip()!r}"
        try:
            raw = float(raw)
        except ValueError:
            return None, f"unparseable value {raw.strip()!r}"
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, f"unparseable value {raw!r}"
    if not math.isfinite(value) or value <= 0:
        return None, f"non-positive or non-finite value ({value})"
    return value, ""


@dataclass
class Anchor:
    """The recommended top concentration and how it was derived. `applicable` False means the anchor could not
    fire: the agent must fall back to the template default and say that it did."""
    applicable: bool
    confidence: str                                   # "high" | "low" | "none"
    reason: str
    flags: list[str] = field(default_factory=list)
    top_concentration_uM: float | None = None
    low_concentration_uM: float | None = None
    series_uM: list[float] = field(default_factory=list)
    dilution_factor: float | None = None
    n_points: int | None = None
    median_ic50_nM: float | None = None
    multiplier: float | None = None
    multiplier_basis: str = ""
    statistic: str = "median (unweighted)"
    weighting: str = "none"
    weighting_reason: str = ("analogs arrive k=3 within a narrow Tanimoto band, a weighted median over 2-3 "
                            "points is a step function of the weights, and similarity-to-potency is not "
                            "calibrated here; the similarities are recorded instead")
    analogs: list[dict] = field(default_factory=list)      # the ones the number came from
    skipped: list[dict] = field(default_factory=list)      # censored / missing, with why
    n_analogs: int = 0
    n_skipped: int = 0
    spread_log10: float | None = None
    template_default_uM: float | None = None
    shift_log10: float | None = None                   # log10(default / anchored top): + = anchor is lower
    agm: dict = field(default_factory=lambda: dict(AGM))
    # Filled by propose.py once the model has answered: did it follow the anchor, and if not, why.
    followed: bool | None = None
    departure_reason: str = ""
    stated_top_uM: float | None = None
    stated_analogs: list[str] = field(default_factory=list)

    @property
    def analog_ids(self) -> list[str]:
        return [str(a.get("compound")) for a in self.analogs if a.get("compound")]

    def rule_context(self) -> dict:
        """The context values `kg.protocols.build_db.check_rule` needs for the potency-prior rules."""
        if self.median_ic50_nM is None:
            return {}
        return {"expected_ic50_uM": self.median_ic50_nM / 1000.0,
                "analog_median_ic50_uM": self.median_ic50_nM / 1000.0}

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, [], "")}

    def sentence(self) -> str:
        """One line for the model and for the trace."""
        if not self.applicable:
            return (f"Analog anchor: not applicable ({self.reason}). Fall back to the template's default top "
                    f"concentration and say in the rationale that you did.")
        ids = ", ".join(self.analog_ids) or "none"
        low = f"{self.low_concentration_uM:g}" if self.low_concentration_uM is not None else "?"
        flags = f" [{', '.join(self.flags)}]" if self.flags else ""
        return (f"Analog anchor{flags}: top {self.top_concentration_uM:g} µM "
                f"= median analog IC50 {self.median_ic50_nM:g} nM x {self.multiplier:g} "
                f"({self.multiplier_basis}), 1:{self.dilution_factor:g} x {self.n_points} points, "
                f"down to {low} µM; from {ids}; confidence {self.confidence}.")


def anchor_from_analogs(analogs: Sequence[dict], shape: Shape | None = None, ranked: bool = True) -> Anchor:
    """The anchor from `bio_kg_analogs`-shaped rows: `{"compound", "ic50_nM", "similarity"}` each.

    `shape` is the template's series shape; without one, the AGM defaults in `DEFAULT_SHAPE` are used for the
    spacing and the point count and the multiplier falls back to `FALLBACK_MULTIPLIER` (a heuristic, flagged).
    `ranked=False` says the analogs are not structural analogs at all but the target's most potent compounds
    (what `bio_kg_analogs` returns for a compound with no usable structure): the anchor still fires, flagged.
    """
    shape = shape or DEFAULT_SHAPE
    used, skipped = [], []
    for a in analogs or []:
        value, why = _value(dict(a))
        entry = {"compound": a.get("compound"), "name": a.get("name"), "ic50_nM": value,
                 "similarity": a.get("similarity")}
        if value is None:
            skipped.append({**{k: v for k, v in entry.items() if k != "ic50_nM"}, "why": why})
        else:
            used.append(entry)

    base = Anchor(applicable=False, confidence="none", reason="", skipped=skipped, n_skipped=len(skipped),
                  dilution_factor=shape.dilution_factor, n_points=shape.n_points,
                  template_default_uM=shape.top_concentration_uM)
    if not used:
        counted = f" ({len(skipped)} analog(s) skipped: censored or missing potency)" if skipped else ""
        base.reason = (f"no analog with a usable IC50 on this target{counted}, so there is no measured scale "
                       f"to centre the series on")
        return base

    values = sorted(a["ic50_nM"] for a in used)
    median = float(statistics.median(values))
    spread = math.log10(values[-1] / values[0]) if values[0] > 0 else None

    flags: list[str] = []
    if len(used) == 1:
        flags.append("single_analog")
    if spread is not None and spread > WIDE_SPREAD_LOG10:
        flags.append("wide_spread")
    if not ranked:
        flags.append("not_ranked_by_similarity")
    if skipped:
        flags.append(f"skipped_{len(skipped)}")

    if shape.dilution_factor and shape.n_points:
        factor, points = float(shape.dilution_factor), int(shape.n_points)
        multiplier = factor ** ((points - 1) / 2)
        basis = (f"centre the series on the median analog potency: {factor:g}"
                 f"**(({points}-1)/2), AGM {AGM['nbk']} half above / half below")
    else:                       # a degenerate shape: the documented heuristic, NOT an AGM number, and the
        # AGM default spacing and point count for the series itself (rule:agm/even_spacing + min_points)
        factor, points = DEFAULT_SHAPE.dilution_factor, DEFAULT_SHAPE.n_points
        multiplier = FALLBACK_MULTIPLIER
        basis = "heuristic 100x the median analog potency (no template shape; TODO(final): not an AGM number)"
        flags.append("heuristic_multiplier")

    top = _sig(median * multiplier / 1000.0, 3)          # nM -> µM
    series = series_from(top, factor, points)
    confidence = "low" if {"single_analog", "wide_spread", "not_ranked_by_similarity",
                           "heuristic_multiplier"} & set(flags) else "high"
    reason = (f"median of {len(used)} analog IC50(s) ({', '.join(f'{v:g}' for v in values)} nM) "
              f"x {multiplier:g}")
    if confidence == "low":
        reason += f"; low confidence: {', '.join(flags)}"

    base.applicable = True
    base.dilution_factor = factor
    base.n_points = points
    base.confidence = confidence
    base.reason = reason
    base.flags = flags
    base.top_concentration_uM = top
    base.low_concentration_uM = series[-1]
    base.series_uM = series
    base.median_ic50_nM = median
    base.multiplier = _sig(multiplier, 4)
    base.multiplier_basis = basis
    base.analogs = used
    base.n_analogs = len(used)
    base.spread_log10 = round(spread, 3) if spread is not None else None
    if shape.top_concentration_uM:
        base.shift_log10 = round(math.log10(shape.top_concentration_uM / top), 3)
    return base


def anchor_from_result(result: dict, shape: Shape | None = None) -> Anchor:
    """The anchor from a whole `bio_kg_analogs` tool result (its `analogs` list and `ranked_by_similarity`)."""
    result = result or {}
    rows = result.get("analogs")
    if rows is None:        # an older result shape: rebuild what we can from the parallel lists
        ic50s = result.get("ic50_nM") or []
        sims = result.get("similarity") or [None] * len(ic50s)
        rows = [{"compound": None, "ic50_nM": v, "similarity": s} for v, s in zip(ic50s, sims)]
    return anchor_from_analogs(rows, shape, ranked=bool(result.get("ranked_by_similarity", True)))


# --- the grader-side check -----------------------------------------------------------------------------------

@dataclass
class Check:
    """A reusable pass/fail with a reason, for the grader (benchmark/) that does not exist yet."""
    passed: bool
    reason: str
    anchor: Anchor | None = None

    def __bool__(self) -> bool:
        return self.passed

    def to_dict(self) -> dict:
        d = {"passed": self.passed, "reason": self.reason}
        if self.anchor is not None:
            d["anchor"] = self.anchor.to_dict()
        return d


_COMPOUND_ID = re.compile(r"^CHEMBL\d+$", re.I)


def _design(experiment: Any) -> tuple[dict, list[str]]:
    """(the experiment's fields, its citations) from an `Experiment`, an `ExperimentProposal` or a dict."""
    data = experiment
    if hasattr(experiment, "model_dump"):
        data = experiment.model_dump()
    if not isinstance(data, dict):
        return {}, []
    citations = [str(c) for c in (data.get("citations") or [])]
    if data.get("experiment"):                      # an ExperimentProposal
        inner = data["experiment"]
        inner = inner.model_dump() if hasattr(inner, "model_dump") else dict(inner)
        return inner, citations
    return data, citations


def check_series_consistent_with_analogs(experiment: Any, analogs: Sequence[dict] | dict,
                                         citations: Iterable[str] | None = None,
                                         cited_analogs: Iterable[str] | None = None,
                                         query_compound: str | None = None,
                                         tolerance_steps: float = TOLERANCE_STEPS) -> Check:
    """Is this concentration series consistent with the analogs that were actually retrieved?

    Catches both failure directions:

    1. **The series ignores the retrieved analogs** - its top concentration is more than `tolerance_steps`
       dilution steps away from the anchor the analogs imply (equivalently: the series is not centred on their
       median potency), or their median falls outside the range the series samples at all.
    2. **The proposal cites analogs it did not actually use** - it names analog node IDs that are not among the
       ones `bio_kg_analogs` returned, so the provenance of the number is fabricated.

    `analogs` is either the list of analog rows or a whole `bio_kg_analogs` result. `cited_analogs` is what the
    proposal says it used (propose.py's `anchor_analogs`); without it, compound-shaped `citations` are used.
    The anchor is recomputed with the **experiment's own** spacing and point count, so a model that chose a
    different shape is judged on the shape it chose.
    """
    design, from_proposal = _design(experiment)
    cites = [str(c) for c in (citations if citations is not None else from_proposal)]
    rows = analogs.get("analogs") if isinstance(analogs, dict) else analogs
    ranked = bool(analogs.get("ranked_by_similarity", True)) if isinstance(analogs, dict) else True
    if isinstance(analogs, dict) and rows is None:
        return check_series_consistent_with_analogs(
            experiment, anchor_from_result(analogs).analogs, citations=cites,
            cited_analogs=cited_analogs, query_compound=query_compound, tolerance_steps=tolerance_steps)
    rows = list(rows or [])

    try:
        top = float(design["top_concentration_uM"])
        factor = float(design["dilution_factor"])
        points = int(design["n_points"])
    except (KeyError, TypeError, ValueError):
        return Check(False, "the proposal has no usable concentration series (top, dilution factor, points)")
    if top <= 0 or factor <= 1 or points < 1:
        return Check(False, f"the series is not a dilution series (top {top}, factor {factor}, {points} points)")

    retrieved = {str(a.get("compound")) for a in rows if a.get("compound")}
    if cited_analogs is None:
        named = [c for c in cites if c in retrieved or _COMPOUND_ID.match(c)]
    else:
        named = [str(c) for c in cited_analogs]
    if query_compound:
        named = [c for c in named if c != str(query_compound)]
    invented = sorted({c for c in named if c not in retrieved})
    if invented:
        return Check(False, f"cites analog(s) that bio_kg_analogs never returned: {', '.join(invented)} "
                            f"(retrieved: {', '.join(sorted(retrieved)) or 'none'})")

    anchor = anchor_from_analogs(rows, Shape(dilution_factor=factor, n_points=points,
                                            top_concentration_uM=top), ranked=ranked)
    if not anchor.applicable:
        return Check(True, f"no analog anchor to be consistent with ({anchor.reason}); the template default "
                           f"stands, so the series cannot contradict the analogs", anchor)

    steps = abs(math.log10(top / anchor.top_concentration_uM)) / math.log10(factor)
    lowest = top / factor ** (points - 1)
    median_uM = anchor.median_ic50_nM / 1000.0
    if not lowest <= median_uM <= top:
        return Check(False, f"the series ({lowest:g}-{top:g} µM) does not even span the analogs' median "
                            f"potency ({anchor.median_ic50_nM:g} nM): it ignores the retrieved analogs",
                     anchor)
    if steps > tolerance_steps:
        return Check(False, f"top {top:g} µM is {steps:.1f} dilution steps from the analog anchor "
                            f"{anchor.top_concentration_uM:g} µM (tolerance {tolerance_steps:g}): the series "
                            f"is not centred on the analogs' median potency "
                            f"({anchor.median_ic50_nM:g} nM)", anchor)
    note = f"; low confidence anchor ({', '.join(anchor.flags)})" if anchor.confidence == "low" else ""
    return Check(True, f"top {top:g} µM is {steps:.1f} dilution steps from the analog anchor "
                       f"{anchor.top_concentration_uM:g} µM, derived from "
                       f"{', '.join(anchor.analog_ids) or f'{anchor.n_analogs} analog(s)'}{note}", anchor)
