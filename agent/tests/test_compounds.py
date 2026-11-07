"""The compound resolver: graph, then the local ChEMBL dump, then the REST API (stubbed here: no network)."""
import json
import sqlite3

import pytest

from agent.compounds import FIELDS, Compound, CompoundResolver


def test_the_graph_comes_first(kb, tmp_path):
    r = CompoundResolver(graph=kb, cache=tmp_path, allow_network=False)
    hit = r.resolve("CMP_A")
    assert hit.id == "CMP_A" and hit.source == "biology KG" and hit.smiles


def test_a_graph_compound_without_smiles_is_still_a_hit(kb, tmp_path):
    hit = CompoundResolver(graph=kb, cache=tmp_path, allow_network=False).resolve("CAND2")
    assert hit.id == "CAND2" and hit.smiles == ""


def test_unknown_compound_offline_resolves_to_nothing(kb, tmp_path):
    r = CompoundResolver(graph=kb, cache=tmp_path, allow_network=False)
    assert r.resolve("ibrutinib") is None
    assert r.smiles_for("ibrutinib") == ("", "unresolved")
    assert any("network lookups are off" in n for n in r.notes)


def _dump(path):
    """A two-table stand-in for the ChEMBL dump: molecule_dictionary + compound_structures, no activities."""
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE molecule_dictionary (molregno INTEGER, chembl_id TEXT, pref_name TEXT);
        CREATE TABLE compound_structures (molregno INTEGER, canonical_smiles TEXT);
        INSERT INTO molecule_dictionary VALUES (1, 'CHEMBL1873475', 'IBRUTINIB');
        INSERT INTO compound_structures VALUES (1, 'C=CC(=O)N1CCCC1');
    """)
    con.commit()
    con.close()


def test_the_local_dump_is_used_when_present(kb, tmp_path, monkeypatch):
    db = tmp_path / "chembl.db"
    _dump(db)
    monkeypatch.setenv("CHEMBL_SQLITE", str(db))
    r = CompoundResolver(graph=kb, cache=tmp_path, allow_network=False)
    for query in ("ibrutinib", "CHEMBL1873475"):
        hit = r.resolve(query)
        assert hit == Compound("CHEMBL1873475", "IBRUTINIB", "C=CC(=O)N1CCCC1", "ChEMBL dump"), query


def test_a_missing_dump_is_noted_not_raised(kb, tmp_path, monkeypatch):
    monkeypatch.setenv("CHEMBL_SQLITE", str(tmp_path / "nope.db"))
    r = CompoundResolver(graph=kb, cache=tmp_path, allow_network=False)
    assert r.resolve("ibrutinib") is None
    assert "no local ChEMBL dump" in r.notes


class StubAPI(CompoundResolver):
    """The REST API without the network."""
    payloads = {"name": {"molecules": [{"molecule_chembl_id": "CHEMBL1873475", "pref_name": "IBRUTINIB",
                                        "canonical_smiles": "C=CC(=O)N1CCCC1"}]},
                "id": {"molecule_chembl_id": "CHEMBL1873475", "pref_name": "IBRUTINIB",
                       "molecule_structures": {"canonical_smiles": "C=CC(=O)N1CCCC1"}}}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        return self.payloads["id" if "/CHEMBL" in url else "name"]


@pytest.mark.parametrize("query", ["ibrutinib", "CHEMBL1873475"])
def test_the_api_is_the_last_resort(tmp_path, monkeypatch, query):
    monkeypatch.setenv("CHEMBL_SQLITE", str(tmp_path / "nope.db"))
    monkeypatch.delenv("WWTN_OFFLINE", raising=False)
    r = StubAPI(graph=None, cache=tmp_path / "cache")
    hit = r.resolve(query)
    assert hit.id == "CHEMBL1873475" and hit.smiles == "C=CC(=O)N1CCCC1" and hit.source == "ChEMBL API"
    # structure fields only: an activity endpoint or field would leak held-out measurements
    assert all("activit" not in u for u in r.urls)
    assert all(f in r.urls[0] for f in ("molecule", "only="))
    for field in FIELDS:
        assert field in r.urls[0]


def test_api_answers_are_cached_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEMBL_SQLITE", str(tmp_path / "nope.db"))
    monkeypatch.delenv("WWTN_OFFLINE", raising=False)
    cache = tmp_path / "cache"
    first = StubAPI(graph=None, cache=cache)
    first.resolve("ibrutinib")
    assert len(first.urls) == 1
    files = list(cache.glob("*.json"))
    assert files and json.loads(files[0].read_text())["molecules"]

    again = StubAPI(graph=None, cache=cache)
    assert again.resolve("ibrutinib").smiles == "C=CC(=O)N1CCCC1"
    assert again.urls == []                      # served from the cache, no second request


def test_an_api_failure_degrades_gracefully(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEMBL_SQLITE", str(tmp_path / "nope.db"))

    monkeypatch.delenv("WWTN_OFFLINE", raising=False)

    class Broken(CompoundResolver):
        def fetch(self, url):
            self.notes.append("ChEMBL API unavailable: URLError")
            return None

    r = Broken(graph=None, cache=tmp_path / "cache")
    assert r.resolve("ibrutinib") is None
    assert any("unavailable" in n for n in r.notes)


def test_offline_env_var_turns_the_network_off(tmp_path, monkeypatch):
    monkeypatch.setenv("WWTN_OFFLINE", "1")   # set by the autouse fixture too; explicit here as the subject
    r = StubAPI(graph=None, cache=tmp_path)
    assert r.allow_network is False
