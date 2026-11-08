"""The shared data contracts between workstreams: what each folder reads and writes.

Change a model here only with a heads-up to the team: benchmark/, agent/ and execution/ all depend on it.
Files on disk are JSON Lines, one model per line:

    benchmark/questions.jsonl     Question            (benchmark/ writes, agent/ reads)
    benchmark/ground_truth.jsonl  GroundTruth         (benchmark/ writes and grades with it; agent/ must not read it)
    agent/out/<run>.jsonl         ExperimentProposal  (agent/ writes, benchmark/ and execution/ read)
    execution/out/<run>/          one OT-2 protocol (.py) + run sheet (.md) per proposal, and ExecutionResult

    from wwtn.schema import ExperimentProposal, read_jsonl, write_jsonl

An `Experiment` describes a panel of species, not one system, and carries its concentration unit rather than
assuming µM (2026-11-08, for the antimicrobial MIC re-framing). Old single-system, µM-only records still load:
`top_concentration_uM` alone is accepted as input, and `system` alone is read as a panel of one.
"""
from pathlib import Path
from typing import Iterable, Literal, TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T", bound=BaseModel)

ConcentrationUnit = Literal["uM", "nM", "ug/mL", "mg/L"]
Atmosphere = Literal["aerobic", "anaerobic", "microaerophilic"]
# How much air a species tolerates during the few minutes of plate setup on the bench. This is a different
# question from the incubation atmosphere and `execution/lab.yaml` keeps them apart for the same reason.
OxygenTolerance = Literal["aerobe", "facultative", "aerotolerant anaerobe", "strict anaerobe", "unknown"]


class Question(BaseModel):
    """A question the knowledge base cannot answer yet, e.g. "Does imatinib inhibit KIT?"."""
    id: str
    text: str
    compound: str | None = None   # an ID from the biology KG where possible (e.g. a ChEMBL ID)
    target: str | None = None     # likewise (e.g. a UniProt accession)
    split: Literal["dev", "test"] = "dev"


class PanelMember(BaseModel):
    """One species (or strain) the compound is tested against, and why it is on the plate.

    `reason` is not decoration: for a selectivity question the panel *is* the answer, so the benchmark grades
    which species were chosen, and a choice without a reason cannot be checked against the graph.
    """
    name: str                             # e.g. "Clostridioides difficile"
    id: str | None = None                 # a biology KG node ID where one exists, e.g. "CHEMBL614965"
    role: Literal["pathogen", "commensal", "pathobiont", "unknown"] = "unknown"
    oxygen_tolerance: OxygenTolerance = "unknown"
    reason: str = ""                      # why this species answers the question; cite a KG node where possible


class PlateLayout(BaseModel):
    """How the proposal wants the plate laid out. Defaults match the team's own MIC protocol.

    `series_axis` is a real constraint, not a preference: an 8-channel pipette moves a whole column at a time,
    so a series running along the rows cannot use it. `execution/feasibility.py` checks this against the lab
    rather than letting the generator quietly produce something the robot cannot do.
    """
    plate_format: int = 96                # wells
    series_axis: Literal["columns", "rows"] = "columns"
    replicates_axis: Literal["rows", "plates"] = "rows"
    control_columns: list[str] = Field(default_factory=lambda: ["growth control", "sterility control"])


class Experiment(BaseModel):
    """The experiment that would answer a question: the fields the benchmark grades one by one.

    Concentration is carried as a value plus a unit, because MIC is reported in µg/mL and enzyme IC50 in µM and
    converting between them needs a molecular weight this model does not have. `top_concentration_uM` remains
    as a convenience for the µM assays that predate the unit field (`agent/anchor.py`, the demo traces): it is
    derived, equal to `top_concentration` when the unit is µM or nM and **None otherwise**, so a reader that
    uses it on a µg/mL experiment gets nothing rather than a number off by a molecular weight.
    """
    assay_type: str                       # e.g. "biochemical enzyme inhibition", "broth microdilution (MIC)"
    readout: str                          # e.g. "luminescence (ATP)", "absorbance 590 nm (turbidity)"
    system: str                           # e.g. "recombinant KIT kinase", "bacterial panel"; see `panel`
    panel: list[PanelMember] = Field(default_factory=list)   # empty for a single-system assay
    top_concentration: float = 0.0
    concentration_unit: ConcentrationUnit = "uM"
    top_concentration_uM: float | None = None   # derived; see the class docstring
    dilution_factor: float                # e.g. 3 for a 1:3 series, 2 for MIC
    n_points: int                         # concentrations in the series
    replicates: int = 3
    controls: list[str] = Field(default_factory=list)   # e.g. ["DMSO vehicle", "staurosporine positive control"]

    # growth and incubation: what the robot cannot do, and what the lab has to be able to provide
    medium: str | None = None             # e.g. "cation-adjusted Mueller-Hinton broth"
    incubation_C: float | None = None
    incubation_h: float | None = None
    atmosphere: Atmosphere | None = None  # the *incubation* atmosphere
    well_volume_uL: float | None = None
    layout: PlateLayout = Field(default_factory=PlateLayout)

    @model_validator(mode="after")
    def _reconcile_concentration(self) -> "Experiment":
        """Keep `top_concentration` canonical and `top_concentration_uM` a faithful derivative of it."""
        micromolar = {"uM": 1.0, "nM": 1e-3}
        if not self.top_concentration and self.top_concentration_uM:
            # written against the old schema: one number, µM implied
            object.__setattr__(self, "top_concentration", self.top_concentration_uM)
            object.__setattr__(self, "concentration_unit", "uM")
        factor = micromolar.get(self.concentration_unit)
        object.__setattr__(self, "top_concentration_uM",
                           None if factor is None else self.top_concentration * factor)
        return self

    def species(self) -> list[str]:
        """The names on the plate: the panel if there is one, otherwise `system` as a panel of one."""
        return [m.name for m in self.panel] or ([self.system] if self.system else [])


class ExperimentProposal(BaseModel):
    """What the agent returns for one Question."""
    question_id: str
    answerable_from_kb: bool              # True if the KB already answers it: then no experiment is needed
    answer: str | None = None             # only when answerable_from_kb
    experiment: Experiment | None = None  # only when not answerable_from_kb
    rationale: str = ""
    citations: list[str] = Field(default_factory=list)  # KG node IDs or protocol IDs the proposal relied on
    model: str = ""                       # which LLM produced it


class GroundTruth(BaseModel):
    """What was actually done (e.g. from a held-out ChEMBL assay), for grading."""
    question_id: str
    experiment: Experiment
    source: str = ""                      # e.g. "CHEMBL assay CHEMBL1234567"


class ExecutionResult(BaseModel):
    """One generated OT-2 protocol and whether it ran in the simulator.

    `run_sheet_path` is not optional in practice: the robot stops once the plate is set up, so a result whose
    run sheet is missing describes an experiment with no measurement in it.
    """
    question_id: str
    protocol_path: str
    simulated_ok: bool
    error: str | None = None
    run_sheet_path: str | None = None
    api_level: str = ""                   # the level it was generated at, which may be below lab.yaml's
    warnings: list[str] = Field(default_factory=list)   # from execution/protocol.py: tips, volumes, deck space


def read_jsonl(path: str | Path, model: type[T]) -> list[T]:
    with open(path, encoding="utf-8") as f:
        return [model.model_validate_json(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, items: Iterable[BaseModel]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
