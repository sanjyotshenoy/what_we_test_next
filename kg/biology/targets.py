"""A ChEMBL target with its UniProt accession and protein-class chain (from the SQLite dump or the REST API)."""
from dataclasses import dataclass

from kg.constants import PROTEIN_KINASE_CLASS


@dataclass(frozen=True)
class ProteinClass:
    id: int
    name: str
    parent_id: int | None
    level: int


@dataclass(frozen=True)
class TargetInfo:
    target_chembl_id: str
    pref_name: str
    uniprot: str
    organism: str
    target_type: str
    classes: list[ProteinClass]   # most specific first, ending at the root

    @property
    def is_protein_kinase(self) -> bool:
        return any(c.id == PROTEIN_KINASE_CLASS for c in self.classes)
