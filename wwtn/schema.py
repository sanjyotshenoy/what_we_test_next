"""The shared data contracts between workstreams: what each folder reads and writes.

Change a model here only with a heads-up to the team: benchmark/, agent/ and execution/ all depend on it.
Files on disk are JSON Lines, one model per line:

    benchmark/questions.jsonl     Question            (benchmark/ writes, agent/ reads)
    benchmark/ground_truth.jsonl  GroundTruth         (benchmark/ writes and grades with it; agent/ must not read it)
    agent/out/<run>.jsonl         ExperimentProposal  (agent/ writes, benchmark/ and execution/ read)
    execution/out/<run>/          one OT-2 protocol (.py) per proposal, plus ExecutionResult lines

    from wwtn.schema import ExperimentProposal, read_jsonl, write_jsonl
"""
from pathlib import Path
from typing import Iterable, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class Question(BaseModel):
    """A question the knowledge base cannot answer yet, e.g. "Does imatinib inhibit KIT?"."""
    id: str
    text: str
    compound: str | None = None   # an ID from the biology KG where possible (e.g. a ChEMBL ID)
    target: str | None = None     # likewise (e.g. a UniProt accession)
    split: Literal["dev", "test"] = "dev"


class Experiment(BaseModel):
    """The experiment that would answer a question: the fields the benchmark grades one by one."""
    assay_type: str                       # e.g. "biochemical enzyme inhibition", "cell viability"; BAO terms where possible
    readout: str                          # e.g. "luminescence (ATP)", "absorbance 570 nm"
    system: str                           # e.g. "recombinant KIT kinase", "K562 cells"
    top_concentration_uM: float
    dilution_factor: float                # e.g. 3 for a 1:3 series
    n_points: int                         # concentrations in the series
    replicates: int = 3
    controls: list[str] = Field(default_factory=list)   # e.g. ["DMSO vehicle", "staurosporine positive control"]


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
    """One generated OT-2 protocol and whether it ran in the simulator."""
    question_id: str
    protocol_path: str
    simulated_ok: bool
    error: str | None = None


def read_jsonl(path: str | Path, model: type[T]) -> list[T]:
    with open(path) as f:
        return [model.model_validate_json(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, items: Iterable[BaseModel]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
