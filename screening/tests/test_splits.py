"""Split integrity: nothing may leak across folds, and the committed files must be the ones the loader reads.

No network: everything runs on screening/tests/fixtures/mic_small.csv, a hand-written 18-row matrix that carries
one of each awkward case (two spellings of one species, a censored `>` row, a `>=` row, a `<` row, a molar value,
a blank value, a row with no organism, an unconvertible unit).
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from screening import splits as S

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MATRIX = FIXTURES / "mic_small.csv"
COMMITTED = Path(__file__).resolve().parents[1] / "splits"


@pytest.fixture
def frame():
    return S.load_matrix(MATRIX)


def test_species_key_collapses_every_spelling_of_one_species():
    assert S.species_key("Staphylococcus aureus subsp. aureus") == "Staphylococcus aureus"
    assert S.species_key("Staphylococcus aureus H37Rv") == "Staphylococcus aureus"
    assert S.species_key("Escherichia coli O157:H7") == "Escherichia coli"
    assert S.species_key("  Bifidobacterium   longum  ") == "Bifidobacterium longum"
    assert S.species_key("unidentified") == "unidentified"   # a single token stays whole, not half a binomial
    assert S.species_key("") == "" and S.species_key(None) == ""


def test_scope_drops_rows_that_cannot_carry_a_prediction(frame):
    assert len(frame) == 16                                  # 18 fixture rows less the two below
    assert (frame["species"] != "").all()                    # the row with no organism is gone
    assert frame["value"].notna().all()                      # the row with a blank value is gone
    assert frame["species"].nunique() == 5                   # the three S. aureus spellings collapsed to one
    assert frame["censored"].sum() == 3                      # >, >=, <


def test_cold_compound_puts_every_measurement_of_a_compound_in_one_fold(frame):
    spec = S.cold_compound(frame, MATRIX)
    folds = spec["ids"]
    assert set(folds) == {"train", "val", "test"}
    everywhere = [c for fold in folds.values() for c in fold]
    assert len(everywhere) == len(set(everywhere)) == frame["molecule_chembl_id"].nunique()
    split = S.Split(spec["name"], spec["unit"], folds, spec)
    assigned = split.assign(frame)
    assert assigned.notna().all()                            # every row is placed
    # The leak test: no compound may appear in two folds' row sets.
    for compound, group in frame.groupby("molecule_chembl_id"):
        assert assigned.loc[group.index].nunique() == 1, f"{compound} spans folds"
    assert sum(spec["row_counts"].values()) == len(frame)


def test_cold_species_holds_out_whole_species_including_b_longum(frame):
    # min_rows/min_compounds are the real thresholds; on an 18-row fixture nothing else qualifies, which is the
    # correct behaviour - it holds out only what it was told to.
    spec = S.cold_species(frame, MATRIX)
    assert "Bifidobacterium longum" in spec["ids"]["test"]
    split = S.Split(spec["name"], spec["unit"], spec["ids"], spec)
    assigned = split.assign(frame)
    for species, group in frame.groupby("species"):
        assert assigned.loc[group.index].nunique() == 1, f"{species} spans folds"
    train = split.subset(frame, "train")
    assert not set(train["species"]) & set(spec["ids"]["test"])
    assert "Bifidobacterium longum" not in set(train["species"])


def test_a_compound_is_allowed_to_span_folds_in_cold_species(frame):
    """The mirror of the test above: cold_species deliberately does *not* hold compounds out. CHEMBL_A is
    measured on S. aureus (train) and B. longum (test), and that is the point of the split."""
    spec = S.cold_species(frame, MATRIX)
    split = S.Split(spec["name"], spec["unit"], spec["ids"], spec)
    rows = frame[frame["molecule_chembl_id"] == "CHEMBL_A"]
    assert set(split.assign(rows).dropna()) == {"train", "test"}


def test_generate_is_reproducible_from_the_seed(frame):
    first = S.cold_compound(frame, MATRIX, seed=7)["ids"]
    assert first == S.cold_compound(frame, MATRIX, seed=7)["ids"]
    # ... and the seed is what fixes it: on a pool big enough for the shuffle to matter, another seed differs.
    wide = pd.DataFrame({"molecule_chembl_id": [f"CHEMBL{i}" for i in range(200)], "species": ["X"] * 200,
                         "value": [1.0] * 200, "censored": [False] * 200})
    assert S.cold_compound(wide, MATRIX, seed=7)["ids"] != S.cold_compound(wide, MATRIX, seed=8)["ids"]


def test_loader_round_trips_a_written_split(frame, tmp_path):
    paths = S.generate(MATRIX, tmp_path, seed=S.SEED)
    assert set(paths) == {"cold_compound", "cold_species"}
    for name in paths:
        split = S.Split.load(name, tmp_path)
        assert split.name == name and split.ids
        assert split.fold_of(next(iter(split.ids["train"]))) == "train"
        assert split.fold_of("nothing-like-an-id") is None   # honest None, not a silent fold
        with pytest.raises(KeyError):
            split.subset(frame, "no-such-fold")


def test_any_split_file_present_is_internally_consistent():
    """No split files are committed - the matrix they are cut from is not in the repo either (see
    screening/README.md). But once somebody generates them on the machine that has the data, they are the
    artifact everyone shares, so check any that are there rather than skipping silently."""
    found = sorted(COMMITTED.glob("*.json"))
    for path in found:
        spec = json.loads(path.read_text())
        ids = [i for fold in spec["ids"].values() for i in fold]
        assert len(ids) == len(set(ids)), f"{path.name}: an ID is in two folds"
        assert spec["seed"] and spec["source"]["sha256"]
        if spec["name"] == "cold_species":
            assert "Bifidobacterium longum" in spec["ids"]["test"]
            assert spec["restricted_to_bacteria"], f"{path.name}: holdouts were picked without a species table"


def test_holdouts_can_be_restricted_to_bacteria(frame):
    """Run on the real matrix without a species table, the mid-sized band is full of fungi, because ChEMBL's MIC
    rows include antifungal assays. `only` is what keeps cold_species measuring what this stage actually asks."""
    unfiltered, _ = S.choose_holdouts(frame, n_extra=4, min_rows=1, min_compounds=1)
    assert "Escherichia coli" in unfiltered           # eligible on data alone
    taxonomy = pd.DataFrame({"species": ["Staphylococcus aureus", "Escherichia coli"],
                             "chembl_l1": ["Bacteria", "Eukaryotes"]})   # E. coli mislabelled on purpose
    only = S.bacteria(taxonomy)
    assert only == {"Staphylococcus aureus"}
    filtered, _ = S.choose_holdouts(frame, n_extra=4, min_rows=1, min_compounds=1, only=only)
    assert "Escherichia coli" not in filtered
    assert "Bifidobacterium longum" in filtered       # the required holdout is never filtered out
    assert S.bacteria(None) is None                   # no table: do not filter, and say so
    assert S.bacteria(pd.DataFrame({"species": ["x"]})) is None


def test_cold_species_records_whether_it_had_a_taxonomy(frame):
    without = S.cold_species(frame, MATRIX)
    assert without["restricted_to_bacteria"] is False and "NOT restricted to bacteria" in without["warning"]
    with_taxonomy = S.cold_species(frame, MATRIX, only={"Staphylococcus aureus"})
    assert with_taxonomy["restricted_to_bacteria"] is True and with_taxonomy["warning"] is None


def test_check_matrix_warns_rather_than_raising_on_a_changed_matrix(frame, tmp_path):
    S.generate(MATRIX, tmp_path, seed=S.SEED)
    split = S.Split.load("cold_compound", tmp_path)
    assert split.check_matrix(MATRIX) == []
    other = tmp_path / "changed.csv"
    other.write_text(MATRIX.read_text() + "CHEMBL_Z,CHEMBL352,Staphylococcus aureus,1280,1.0,ug.mL-1,=,MIC,"
                                          "DOC9,2025,AS99,False\n")
    warnings = split.check_matrix(other)
    assert len(warnings) == 1 and "comparable" in warnings[0]
