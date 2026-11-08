"""Regression coverage for local MIC extraction and API pagination."""
import sqlite3

import pytest

from kg.biology import chembl_api
from kg.biology.chembl_bacteria_db import ChemblBacteriaDB
from kg.biology.build_bacteria import graph_frames, usable
from kg.biology.tests.test_build_bacteria import activity, ORGANISMS
from kg.graph_io import write_graph, read_graph


def test_sqlite_source_preserves_censoring_and_filters_compounds(tmp_path):
    path = tmp_path / 'chembl.db'
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE target_dictionary (tid, chembl_id, target_type);
        CREATE TABLE assays (assay_id, tid, chembl_id, description, bao_format);
        CREATE TABLE activities (activity_id, assay_id, molregno, doc_id,
                                 standard_type, standard_value, standard_units, standard_relation);
        CREATE TABLE docs (doc_id, chembl_id, year, journal);
        CREATE TABLE molecule_dictionary (molregno, chembl_id, pref_name);
        CREATE TABLE compound_structures (molregno, canonical_smiles);
        INSERT INTO target_dictionary VALUES (1, 'ORG', 'ORGANISM'), (2, 'PROTEIN', 'SINGLE PROTEIN');
        INSERT INTO assays VALUES (1, 1, 'ASSAY', 'MIC assay', 'BAO'), (2, 2, 'ASSAY2', '', '');
        INSERT INTO docs VALUES (1, 'DOC', 2025, 'Journal');
        INSERT INTO molecule_dictionary VALUES (1, 'C1', 'Compound'), (2, 'C2', NULL);
        INSERT INTO compound_structures VALUES (1, 'CC');
        INSERT INTO activities VALUES
            (1, 1, 1, 1, 'MIC', 128, 'ug.mL-1', '>'),
            (2, 1, 2, 1, 'MIC', 400, 'nM', '='),
            (3, 1, 1, 1, 'IC50', 1, 'nM', '='),
            (4, 2, 1, 1, 'MIC', 1, 'nM', '=');
    """)
    con.close()
    db = ChemblBacteriaDB(path)
    try:
        assert len(db.activities('ORG')) == 2
        rows = db.activities('ORG', compounds=['C1', 'C1'])
        assert len(rows) == 1
        assert rows[0]['standard_relation'] == '>'
        assert rows[0]['document_year'] == 2025  # no implicit hold-out
        assert db.activities('ORG', compounds=[]) == []
        assert db.activities('PROTEIN') == []
        assert db.molecules(['C1', 'C2']) == {
            'C1': {'name': 'Compound', 'smiles': 'CC'}, 'C2': {'name': '', 'smiles': ''}}
        assert db.molecules([]) == {}
    finally:
        db.con.close()


def test_filtered_api_activities_paginate(monkeypatch):
    urls = []
    monkeypatch.setattr(chembl_api, 'PAGE', 2)
    def get(url):
        urls.append(url)
        return {'activities': [{'activity_id': 3}] if 'offset=2' in url else
                [{'activity_id': 1}, {'activity_id': 2}]}
    monkeypatch.setattr(chembl_api, '_get', get)
    result = chembl_api.ChemblAPI(pause=0).activities('ORG', compounds=['C1'])
    assert len(result) == 3
    assert len(urls) == 2
    assert all('molecule_chembl_id__in=C1' in url for url in urls)


@pytest.mark.parametrize('value', [0, -1, '0', 'nan', 'inf', 'bad', None])
def test_invalid_mic_values_are_rejected(value):
    assert not usable(activity(standard_value=value))


def test_empty_graph_roundtrip(tmp_path):
    nodes, edges = graph_frames([], ORGANISMS)
    write_graph(tmp_path, nodes, edges)
    loaded_nodes, loaded_edges = read_graph(tmp_path)
    assert len(loaded_nodes) == 2
    assert loaded_edges == []
