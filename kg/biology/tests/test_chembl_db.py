import sqlite3

import pytest

from kg.biology.chembl_db import ChemblDB

SCHEMA = """
CREATE TABLE docs (doc_id INTEGER PRIMARY KEY, chembl_id TEXT, year INTEGER, pubmed_id INTEGER, doi TEXT,
                   title TEXT, journal TEXT, doc_type TEXT, abstract TEXT);
CREATE TABLE target_dictionary (tid INTEGER PRIMARY KEY, chembl_id TEXT, pref_name TEXT, target_type TEXT,
                                organism TEXT);
CREATE TABLE component_sequences (component_id INTEGER PRIMARY KEY, accession TEXT);
CREATE TABLE target_components (tid INTEGER, component_id INTEGER);
CREATE TABLE protein_classification (protein_class_id INTEGER PRIMARY KEY, parent_id INTEGER, pref_name TEXT,
                                     class_level INTEGER);
CREATE TABLE component_class (component_id INTEGER, protein_class_id INTEGER);
CREATE TABLE assays (assay_id INTEGER PRIMARY KEY, chembl_id TEXT, description TEXT, assay_type TEXT,
                     bao_format TEXT, tid INTEGER, doc_id INTEGER, variant_id INTEGER);
CREATE TABLE molecule_dictionary (molregno INTEGER PRIMARY KEY, chembl_id TEXT, pref_name TEXT);
CREATE TABLE compound_structures (molregno INTEGER PRIMARY KEY, canonical_smiles TEXT);
CREATE TABLE activities (activity_id INTEGER PRIMARY KEY, assay_id INTEGER, doc_id INTEGER, molregno INTEGER,
                         standard_type TEXT, standard_relation TEXT, standard_value REAL, standard_units TEXT,
                         pchembl_value REAL, data_validity_comment TEXT);
"""


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "mini_chembl.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?)", [
        (1, "CHEMBL_D2010", 2010, 111, "10.1/a", "Old paper", "J Med Chem", "PUBLICATION", ""),
        (2, "CHEMBL_D2020", 2020, 222, "10.1/b", "Newer paper", "J Med Chem", "PUBLICATION", ""),
        (3, "CHEMBL_D2024", 2024, 333, "10.1/c", "Held-out paper", "J Med Chem", "PUBLICATION", ""),
    ])
    con.executemany("INSERT INTO target_dictionary VALUES (?,?,?,?,?)", [
        (10, "CHEMBL1936", "Mast/stem cell growth factor receptor Kit", "SINGLE PROTEIN", "Homo sapiens"),
        (11, "CHEMBL_MOUSE", "Kit (mouse)", "SINGLE PROTEIN", "Mus musculus"),
    ])
    con.execute("INSERT INTO component_sequences VALUES (255, 'P10721')")
    con.executemany("INSERT INTO target_components VALUES (?,?)", [(10, 255), (11, 255)])
    con.executemany("INSERT INTO protein_classification VALUES (?,?,?,?)", [
        (0, None, "Protein class", 0), (1, 0, "Enzyme", 1), (6, 1, "Kinase", 2), (1100, 6, "Protein Kinase", 3),
        (1285, 1100, "TK protein kinase group", 4), (159, 1285, "Tyrosine protein kinase PDGFR family", 5),
    ])
    con.execute("INSERT INTO component_class VALUES (255, 159)")
    con.executemany("INSERT INTO assays VALUES (?,?,?,?,?,?,?,?)", [
        (100, "CHEMBL_A1", "Inhibition of KIT", "B", "BAO_0000357", 10, 1, None),
        (101, "CHEMBL_A2", "Inhibition of KIT", "B", "BAO_0000357", 10, 2, None),
        (102, "CHEMBL_A3", "Inhibition of KIT", "B", "BAO_0000357", 10, 3, None),
        (103, "CHEMBL_A4", "Inhibition of KIT D816V mutant", "B", "BAO_0000357", 10, 1, 77),
    ])
    con.executemany("INSERT INTO molecule_dictionary VALUES (?,?,?)", [
        (1, "CHEMBL941", "IMATINIB"), (2, "CHEMBL2", None), (3, "CHEMBL3", None)])
    con.executemany("INSERT INTO compound_structures VALUES (?,?)", [(1, "CCO"), (2, "CCN"), (3, "CCC")])
    con.executemany("INSERT INTO activities VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (1000, 100, 1, 1, "IC50", "=", 100.0, "nM", 7.0, None),       # 2010, kept
        (1001, 101, 2, 2, "IC50", "=", 5.0, "nM", 8.3, None),         # 2020, kept, newest first
        (1002, 102, 3, 3, "IC50", "=", 1.0, "nM", 9.0, None),         # 2024: held out
        (1003, 100, 1, 3, "IC50", ">", 10000.0, "nM", None, None),    # censored
        (1004, 100, 1, 3, "IC50", "=", 50.0, "%", None, None),        # wrong units
        (1005, 100, 1, 3, "Ki", "=", 50.0, "nM", 7.3, None),          # not an IC50
        (1006, 100, 1, 3, "IC50", "=", 60.0, "nM", 7.2, "Outside typical range"),
        (1007, 100, 1, 3, "IC50", "=", 70.0, "nM", 7.1, "Manually validated"),   # good data: kept
        (1008, 103, 1, 3, "IC50", "=", 80.0, "nM", 7.1, None),                   # mutant assay: dropped
    ])
    con.commit()
    con.close()
    return ChemblDB(path)


def test_activities_cutoff_filters_and_order(db):
    frame = db.activities("CHEMBL1936", before_year=2024)
    assert list(frame["activity_id"]) == [1001, 1000, 1007]
    rows = frame.to_dict("records")
    first = rows[0]
    assert first["molecule_chembl_id"] == "CHEMBL2"
    assert first["canonical_smiles"] == "CCN"
    assert first["assay_chembl_id"] == "CHEMBL_A2"
    assert first["document_chembl_id"] == "CHEMBL_D2020"
    assert first["document_year"] == 2020
    assert first["standard_value"] == 5.0
    assert first["bao_format"] == "BAO_0000357"
    assert rows[1]["molecule_pref_name"] == "IMATINIB"


def test_activities_limit(db):
    assert list(db.activities("CHEMBL1936", before_year=2024, limit=1)["activity_id"]) == [1001]


def test_target_info(db):
    info = db.target_info("CHEMBL1936")
    assert info.uniprot == "P10721"
    assert [c.id for c in info.classes] == [159, 1285, 1100, 6, 1, 0]
    assert info.is_protein_kinase


def test_target_info_not_human(db):
    assert db.target_info("CHEMBL_MOUSE") is None


def test_documents(db):
    docs = db.documents(["CHEMBL_D2010", "CHEMBL_D2020"])
    assert set(docs["document_chembl_id"]) == {"CHEMBL_D2010", "CHEMBL_D2020"}
    old = docs.set_index("document_chembl_id").loc["CHEMBL_D2010"].to_dict()
    assert old == {"year": 2010, "pubmed_id": 111, "doi": "10.1/a", "title": "Old paper", "journal": "J Med Chem"}


def test_class_chain_stops_on_cycle_and_missing_parent(tmp_path):
    path = tmp_path / "cyclic.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO target_dictionary VALUES (10, 'CHEMBL_A', 'A', 'SINGLE PROTEIN', 'Homo sapiens')")
    con.execute("INSERT INTO target_dictionary VALUES (11, 'CHEMBL_B', 'B', 'SINGLE PROTEIN', 'Homo sapiens')")
    con.executemany("INSERT INTO component_sequences VALUES (?, ?)", [(1, 'P1'), (2, 'P2')])
    con.executemany("INSERT INTO target_components VALUES (?, ?)", [(10, 1), (11, 2)])
    con.executemany("INSERT INTO protein_classification VALUES (?,?,?,?)", [
        (5, 6, "child", 2), (6, 5, "loops back", 1),      # a cycle
        (7, 999, "orphan", 1)])                            # parent row missing
    con.executemany("INSERT INTO component_class VALUES (?, ?)", [(1, 5), (2, 7)])
    con.commit()
    con.close()
    db = ChemblDB(path)
    assert [c.id for c in db.target_info("CHEMBL_A").classes] == [5, 6]
    assert [c.id for c in db.target_info("CHEMBL_B").classes] == [7]
