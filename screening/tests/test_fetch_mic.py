"""The fetcher's offline parts: the shard plan, row shaping and the censoring flag. Nothing here touches the API.

The one thing a test can really protect here is the shard plan - a gap or an overlap in it would silently lose or
duplicate thousands of rows in a 45-minute download, and the CSV would look perfectly fine.
"""
import csv
import gzip
import sqlite3

import pytest

from screening import fetch_mic as F

# Just the tables and columns MIC_SQL touches, so the query can be exercised without the 30 GB dump. A row per
# case that matters: a censored reading, a CELL-LINE target the ORGANISM filter must drop, a non-MIC activity, and
# an activity with no document.
FAKE_DUMP = """
CREATE TABLE activities (activity_id INTEGER, assay_id INTEGER, molregno INTEGER, doc_id INTEGER,
                         standard_type TEXT, standard_value REAL, standard_units TEXT, standard_relation TEXT);
CREATE TABLE assays (assay_id INTEGER, tid INTEGER, chembl_id TEXT);
CREATE TABLE target_dictionary (tid INTEGER, chembl_id TEXT, organism TEXT, tax_id INTEGER, target_type TEXT);
CREATE TABLE molecule_dictionary (molregno INTEGER, chembl_id TEXT);
CREATE TABLE compound_structures (molregno INTEGER, canonical_smiles TEXT);
CREATE TABLE compound_properties (molregno INTEGER, full_mwt REAL);
CREATE TABLE docs (doc_id INTEGER, chembl_id TEXT, year INTEGER);
INSERT INTO target_dictionary VALUES (1,'CHEMBL613911','Bifidobacterium longum',216816,'ORGANISM'),
                                     (2,'CHEMBL352','Staphylococcus aureus',1280,'ORGANISM'),
                                     (3,'CHEMBL9999','Homo sapiens',9606,'CELL-LINE');
INSERT INTO molecule_dictionary VALUES (10,'CHEMBL_A'),(11,'CHEMBL_B');
INSERT INTO compound_structures VALUES (10,'CCOc1ccccc1C(=O)N');
INSERT INTO compound_properties VALUES (10,165.19);
INSERT INTO docs VALUES (100,'DOC1',2019);
INSERT INTO assays VALUES (1000,1,'AS1'),(1001,2,'AS2'),(1002,3,'AS3');
INSERT INTO activities VALUES (1,1000,10,100,'MIC',128.0,'ug.mL-1','>'),
                              (2,1001,10,100,'MIC',2.0,'ug.mL-1','='),
                              (3,1001,11,NULL,'MIC',8.0,'ug.mL-1','='),
                              (4,1002,10,100,'MIC',4.0,'ug.mL-1','='),
                              (5,1001,10,100,'IC50',50.0,'nM','=');
"""


@pytest.fixture
def fake_dump(tmp_path):
    path = tmp_path / "chembl_37.db"
    connection = sqlite3.connect(path)
    connection.executescript(FAKE_DUMP)
    connection.commit()
    connection.close()
    return path


@pytest.mark.parametrize("total,workers", [(798852, 6), (798852, 1), (2500, 6), (1, 6), (10000, 4), (1000, 3)])
def test_shard_plan_covers_the_range_exactly_once(total, workers):
    ranges = F.shard_ranges(total, workers, page=1000)
    assert ranges[0][0] == 0 and ranges[-1][1] == total
    assert all(stop > start for start, stop in ranges)
    assert all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), "a gap or an overlap between shards"
    assert sum(stop - start for start, stop in ranges) == total
    assert len(ranges) <= workers


def test_shards_start_on_page_boundaries():
    """Every shard but the first starts at a multiple of the page size, so no request straddles two shards."""
    for start, _ in F.shard_ranges(798852, 6, page=1000)[1:]:
        assert start % 1000 == 0


def test_censored_covers_every_bound_relation():
    assert all(F.censored(r) for r in (">", "<", ">=", "<=", " > "))
    assert not any(F.censored(r) for r in ("=", "~", "", None))


def test_to_row_shape_and_renaming():
    row = F.to_row({"molecule_chembl_id": "CHEMBL25", "target_chembl_id": "CHEMBL352",
                    "target_organism": "Staphylococcus aureus", "target_tax_id": 1280, "standard_value": "4.0",
                    "standard_units": "ug.mL-1", "standard_relation": ">", "standard_type": "MIC",
                    "document_chembl_id": "CHEMBL1122", "document_year": 2019, "assay_chembl_id": "CHEMBL8"})
    assert list(row) == F.COLUMNS
    assert row["year"] == 2019 and row["censored"] is True   # document_year is renamed to `year`
    assert row["target_tax_id"] == 1280


def test_to_row_turns_missing_fields_into_empty_strings():
    """ChEMBL returns null for a target with no organism; the CSV must still have every column."""
    row = F.to_row({"molecule_chembl_id": "CHEMBL25", "target_organism": None, "standard_relation": None})
    assert list(row) == F.COLUMNS
    assert row["target_organism"] == "" and row["year"] == "" and row["censored"] is False


def test_concatenate_joins_parts_with_one_header(tmp_path):
    out = tmp_path / "mic.csv"
    parts = []
    for index, molecule in enumerate(("CHEMBL_A", "CHEMBL_B")):
        part = tmp_path / f"part{index}.csv"
        with open(part, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=F.COLUMNS)
            writer.writerow(F.to_row({"molecule_chembl_id": molecule}))
        parts.append(part)
    assert F._concatenate(out, parts) == 2
    with open(out, encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == F.COLUMNS                              # exactly one header, from the concatenator
    assert [r[0] for r in rows[1:]] == ["CHEMBL_A", "CHEMBL_B"]   # parts stay in offset order


# --- the local SQLite source -------------------------------------------------------------------------------

def test_sqlite_source_gives_the_same_columns_as_the_rest_source(fake_dump, tmp_path):
    out = tmp_path / "data" / "mic_matrix.csv"
    state = F.download_sqlite(out, fake_dump)
    with open(out, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == F.COLUMNS                        # the two sources must be interchangeable
    assert state["rows"] == len(rows) == 3
    # The ORGANISM filter dropped the CELL-LINE target, and standard_type='MIC' dropped the IC50.
    assert {r["target_chembl_id"] for r in rows} == {"CHEMBL613911", "CHEMBL352"}
    assert [r["censored"] for r in rows] == ["True", "False", "False"]


def test_sqlite_source_handles_a_row_with_no_document(fake_dump, tmp_path):
    """`docs` is a LEFT JOIN, so an activity with no paper must still produce a row - with empty provenance, not
    a crash and not a dropped measurement."""
    out = tmp_path / "mic.csv"
    F.download_sqlite(out, fake_dump)
    with open(out, encoding="utf-8") as handle:
        orphan = [r for r in csv.DictReader(handle) if r["molecule_chembl_id"] == "CHEMBL_B"][0]
    assert orphan["document_chembl_id"] == "" and orphan["year"] == ""
    assert orphan["standard_value"] == "8.0"


def test_sqlite_source_writes_the_smiles_cache_features_reads(fake_dump, tmp_path):
    """The dump brings structures along, which is the point of preferring it: it replaces ~116k REST lookups."""
    out = tmp_path / "mic.csv"
    smiles = tmp_path / "smiles.csv.gz"
    state = F.download_sqlite(out, fake_dump, smiles_out=smiles)
    with gzip.open(smiles, "rt", encoding="utf-8") as handle:
        cached = list(csv.DictReader(handle))
    assert list(cached[0]) == F.SMILES_COLUMNS
    assert cached == [{"molecule_chembl_id": "CHEMBL_A", "canonical_smiles": "CCOc1ccccc1C(=O)N",
                       "full_mwt": "165.19"}]
    assert state["compounds_with_smiles"] == 1               # CHEMBL_B has no structure row, and is not invented


def test_sqlite_path_resolution(fake_dump, monkeypatch):
    monkeypatch.delenv("CHEMBL_SQLITE", raising=False)
    assert F.sqlite_path(fake_dump) == fake_dump
    monkeypatch.setenv("CHEMBL_SQLITE", str(fake_dump))      # the same env var kg/biology/chembl_db.py honours
    assert F.sqlite_path() == fake_dump
    monkeypatch.delenv("CHEMBL_SQLITE")
    assert F.sqlite_path() is None                           # no dump here: `auto` falls back to REST
    with pytest.raises(FileNotFoundError):
        F.sqlite_path("/nonexistent/chembl_37.db")           # asked for by name: say so, never silently fall back
