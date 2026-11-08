"""The fetcher's offline parts: the shard plan, row shaping and the censoring flag. Nothing here touches the API.

The one thing a test can really protect here is the shard plan - a gap or an overlap in it would silently lose or
duplicate thousands of rows in a 45-minute download, and the CSV would look perfectly fine.
"""
import csv

import pytest

from screening import fetch_mic as F


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
