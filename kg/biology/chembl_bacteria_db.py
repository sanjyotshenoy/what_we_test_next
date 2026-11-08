"""Read bacterial MICs from the local ChEMBL dump in the REST client's row format."""
from typing import Iterable

from kg.biology.chembl_db import ChemblDB


class ChemblBacteriaDB(ChemblDB):
    def activities(self, target_chembl_id: str, standard_type: str = "MIC",
                   compounds: Iterable[str] | None = None) -> list[dict]:
        ids = None if compounds is None else sorted(set(compounds))
        if ids == []:
            return []
        batches = [None] if ids is None else [ids[i:i + 500] for i in range(0, len(ids), 500)]
        rows = []
        for batch in batches:
            sql = """
                SELECT act.activity_id, md.chembl_id AS molecule_chembl_id,
                       td.chembl_id AS target_chembl_id, act.standard_value,
                       act.standard_units, act.standard_relation,
                       d.chembl_id AS document_chembl_id, d.year AS document_year,
                       d.journal AS document_journal, a.chembl_id AS assay_chembl_id,
                       a.description AS assay_description, a.bao_format
                FROM target_dictionary td
                JOIN assays a ON a.tid = td.tid
                JOIN activities act ON act.assay_id = a.assay_id
                JOIN molecule_dictionary md ON md.molregno = act.molregno
                LEFT JOIN docs d ON d.doc_id = act.doc_id
                WHERE td.chembl_id = ? AND td.target_type = 'ORGANISM'
                  AND act.standard_type = ?
            """
            params = [target_chembl_id, standard_type]
            if batch is not None:
                sql += f" AND md.chembl_id IN ({','.join('?' for _ in batch)})"
                params.extend(batch)
            sql += " ORDER BY act.activity_id"
            rows.extend(dict(row) for row in self.con.execute(sql, params))
        return rows

    def molecules(self, compound_ids: Iterable[str]) -> dict[str, dict]:
        ids = sorted(set(compound_ids))
        result = {}
        for i in range(0, len(ids), 500):
            batch = ids[i:i + 500]
            rows = self.con.execute(
                "SELECT md.chembl_id, md.pref_name, cs.canonical_smiles "
                "FROM molecule_dictionary md LEFT JOIN compound_structures cs "
                "ON cs.molregno = md.molregno "
                f"WHERE md.chembl_id IN ({','.join('?' for _ in batch)})", batch)
            for row in rows:
                result[row['chembl_id']] = {
                    'name': row['pref_name'] or '', 'smiles': row['canonical_smiles'] or ''}
        return result
