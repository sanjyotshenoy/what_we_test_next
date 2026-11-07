"""Read the local ChEMBL SQLite dump: the same row shapes the ChEMBL REST API gives, in milliseconds.

Get the dump once (about 5.8 GB download, 30 GB unpacked; git-ignored):

    https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/chembl_37_sqlite.tar.gz
    -> unpack into data/raw/chembl/ at the repo root (git-ignored), giving
       data/raw/chembl/chembl_37/chembl_37_sqlite/chembl_37.db   (or point CHEMBL_SQLITE at the .db file)
"""
import os
import sqlite3
from pathlib import Path

import kg  # noqa: F401  - picks CPU or GPU mode before pandas is imported
import pandas as pd

from kg.biology.targets import ProteinClass, TargetInfo
from kg.constants import CAP_PER_TARGET

DEFAULT_PATH = Path("data/raw/chembl/chembl_37/chembl_37_sqlite/chembl_37.db")

# Checked against the real ChEMBL 37 dump (2026-11-07). Keeps rows with no validity flag or "Manually validated"
# (35 IC50s in all of ChEMBL); drops mutant assays (assays.variant_id set; ~0.5% of IC50s on the seed targets),
# so the potency prior describes the wild-type protein.
ACTIVITIES_SQL = """
SELECT act.activity_id, md.chembl_id AS molecule_chembl_id, md.pref_name AS molecule_pref_name,
       cs.canonical_smiles, td.chembl_id AS target_chembl_id, a.chembl_id AS assay_chembl_id,
       a.description AS assay_description, a.assay_type, a.bao_format, act.standard_value,
       d.chembl_id AS document_chembl_id, d.year AS document_year, act.pchembl_value
FROM activities act
JOIN assays a ON a.assay_id = act.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN docs d ON d.doc_id = act.doc_id
JOIN molecule_dictionary md ON md.molregno = act.molregno
LEFT JOIN compound_structures cs ON cs.molregno = act.molregno
WHERE td.chembl_id = ? AND act.standard_type = 'IC50' AND act.standard_relation = '='
  AND act.standard_units = 'nM' AND act.standard_value IS NOT NULL
  AND (act.data_validity_comment IS NULL OR act.data_validity_comment = 'Manually validated')
  AND a.variant_id IS NULL
  AND d.year IS NOT NULL AND d.year < ?
ORDER BY d.year DESC, act.pchembl_value IS NULL, act.activity_id
LIMIT ?
"""


class ChemblDB:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or os.environ.get("CHEMBL_SQLITE") or DEFAULT_PATH)
        if not self.path.exists():
            raise FileNotFoundError(f"ChEMBL SQLite dump not found at {self.path} (see kg/biology/chembl_db.py)")
        self.con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self.con.row_factory = sqlite3.Row

    def activities(self, target_chembl_id: str, before_year: int, limit: int = CAP_PER_TARGET) -> pd.DataFrame:
        """IC50s (=, nM, valid) on the target from documents published before `before_year`: newest first,
        rows with a pChEMBL value first within a year (the same order as kg.biology.build_seed.cap)."""
        return pd.read_sql_query(ACTIVITIES_SQL, self.con, params=(target_chembl_id, before_year, limit))

    def target_info(self, target_chembl_id: str) -> TargetInfo | None:
        target = self.con.execute(
            "SELECT tid, chembl_id, pref_name, target_type, organism FROM target_dictionary WHERE chembl_id = ?",
            (target_chembl_id,)).fetchone()
        if target is None or target["target_type"] != "SINGLE PROTEIN" or target["organism"] != "Homo sapiens":
            return None
        component = self.con.execute(
            "SELECT cs.component_id, cs.accession FROM target_components tc "
            "JOIN component_sequences cs ON cs.component_id = tc.component_id WHERE tc.tid = ? "
            "ORDER BY cs.component_id LIMIT 1", (target["tid"],)).fetchone()
        start = self.con.execute(
            "SELECT pc.protein_class_id FROM component_class cc "
            "JOIN protein_classification pc ON pc.protein_class_id = cc.protein_class_id "
            "WHERE cc.component_id = ? ORDER BY pc.class_level DESC, pc.protein_class_id LIMIT 1",
            (component["component_id"],)).fetchone()
        classes, seen, class_id = [], set(), start["protein_class_id"] if start else None
        while class_id is not None and class_id not in seen:   # stop on a cycle or a missing parent row
            seen.add(class_id)
            c = self.con.execute("SELECT protein_class_id, pref_name, parent_id, class_level "
                                 "FROM protein_classification WHERE protein_class_id = ?", (class_id,)).fetchone()
            if c is None:
                break
            classes.append(ProteinClass(c["protein_class_id"], c["pref_name"], c["parent_id"], c["class_level"]))
            class_id = c["parent_id"]
        return TargetInfo(target["chembl_id"], target["pref_name"], component["accession"], target["organism"],
                          target["target_type"], classes)

    def documents(self, document_chembl_ids: list[str]) -> pd.DataFrame:
        ids = list(document_chembl_ids)
        frames = [pd.read_sql_query(
            "SELECT chembl_id AS document_chembl_id, year, pubmed_id, doi, title, journal FROM docs "
            f"WHERE chembl_id IN ({','.join('?' * len(batch))})", self.con, params=batch)
            for batch in (ids[i:i + 500] for i in range(0, len(ids), 500))]
        columns = ["document_chembl_id", "year", "pubmed_id", "doi", "title", "journal"]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
