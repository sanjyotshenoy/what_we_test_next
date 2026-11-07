"""The PubChem client's parsing and caching, against two recorded description JSONs (no network).

The fixtures are real /assay/aid/<aid>/description/JSON responses (AIDs 623998 and 1691) cut down to the fields
the protocol DB reads, with at most 12 tested-concentration result columns, so they stay small.
"""
import json
from pathlib import Path

import pytest

from kg.protocols.pubchem import PubChem, parse_description, series_stats

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(aid: int) -> dict:
    return json.loads((FIXTURES / f"aid_{aid}_description.json").read_text())


@pytest.fixture
def offline(tmp_path):
    """An offline client whose cache already holds the two fixtures."""
    client = PubChem(cache=tmp_path, offline=True)
    for aid in (623998, 1691):
        file = tmp_path / f"aid/{aid}/description.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(fixture(aid)))
    return client


def test_parse_text_fields():
    record = parse_description(fixture(623998))
    assert record["aid"] == 623998
    assert record["source"] == "Broad Institute"
    assert record["outcome_method"] == "confirmatory"
    assert "Dispense 20 uL/well of KBAPE" in record["protocol"]
    assert record["name"].startswith("GSK3beta Measured in Biochemical System")


def test_parse_targets():
    record = parse_description(fixture(623998))
    assert record["targets"] == [{"name": "glycogen synthase kinase-3 beta", "accession": "NP_002084.2",
                                  "gene_id": None, "taxid": None}]
    assert parse_description(fixture(1691))["targets"] == []   # some AIDs name no protein target


def test_parse_series_is_uM_and_rejects_other_units():
    record = parse_description(fixture(1691))
    series = record["series"][0]
    assert series["top_uM"] == pytest.approx(40.0)
    assert series["n_points"] == 10
    assert series["dilution_factor"] == pytest.approx(3.0, abs=0.1)
    # a concentration column in an unmapped unit code is skipped, not guessed
    data = fixture(1691)
    for column in data["PC_AssayContainer"][0]["assay"]["descr"]["results"]:
        column["tc"]["unit"] = 7
    assert parse_description(data)["series"] == []


def test_series_stats_marks_interleaved_series_irregular():
    regular = series_stats([0.0015, 0.0046, 0.0135, 0.042, 0.12, 0.38, 1.1, 3.5, 10.0])
    assert regular["regular"] and regular["dilution_factor"] == pytest.approx(3.0, abs=0.05)
    rounded = series_stats([0.002, 0.006, 0.02, 0.05, 0.2, 0.5, 1.0, 4.0, 10.0, 40.0])   # a rounded 1:3 series
    assert rounded["regular"] and rounded["dilution_factor"] == pytest.approx(3.0, abs=0.1)
    interleaved = series_stats([0.00075, 0.0021, 0.0068, 0.0075, 0.0195, 0.021, 0.06, 0.068, 46.0])
    assert not interleaved["regular"] and interleaved["dilution_factor"] is None
    assert series_stats([])["n_points"] == 0
    assert series_stats([0.0, -1.0])["top_uM"] is None


def test_offline_client_reads_cache_and_refuses_misses(offline):
    assert offline.assay(623998)["aid"] == 623998
    with pytest.raises(FileNotFoundError):
        offline.assay(99999999)


def test_candidates_filters_by_outcome_and_cutoff(offline, monkeypatch):
    rows = {
        623998: {"activityoutcomemethod": "Confirmatory", "depositdate": "2012/04/04 00:00",
                 "currentsourcename": "Broad Institute", "assayname": "GSK3beta"},
        1691: {"activityoutcomemethod": "Screening", "depositdate": "2009/04/21 00:00",
               "currentsourcename": "Scripps", "assayname": "JAK2V617F"},
        4242: {"activityoutcomemethod": "Confirmatory", "depositdate": "2025/01/01 00:00",
               "currentsourcename": "Late", "assayname": "after the cutoff"},
    }
    monkeypatch.setattr(offline, "search", lambda term, retmax=200: [623998, 1691, 4242])
    monkeypatch.setattr(offline, "summaries", lambda aids: rows)
    found = offline.candidates({"pubchem": {"search": ["anything"]}})
    assert [r["aid"] for r in found] == [623998]       # 1691 not confirmatory, 4242 past the hold-out cutoff
    assert found[0]["deposited"] == "2012/04/04"
