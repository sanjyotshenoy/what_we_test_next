"""Metric correctness on hand-checked numbers, unit conversion, and how censored rows are handled.

Every expected value below was worked out by hand (the arithmetic is in the comments), because a metric that is
only checked against itself will happily be wrong in the same direction forever. No network.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from screening import baseline as B
from screening import splits as S

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MATRIX = FIXTURES / "mic_small.csv"
SMILES = FIXTURES / "smiles_small.csv"


@pytest.fixture
def prepared():
    return B.prepare(S.load_matrix(MATRIX), SMILES)


# --- unit conversion ---------------------------------------------------------------------------------------

def test_to_ugml_mass_and_molar():
    assert B.to_ugml(4.0, "ug.mL-1", None) == 4.0
    assert B.to_ugml(0.002, "mg.mL-1", None) == pytest.approx(2.0)      # 0.002 mg/mL = 2 ug/mL
    # 10,000 nM of a 117.15 g/mol compound: 1e-5 mol/L x 117.15 g/mol = 1.1715e-3 g/L = 1.1715 ug/mL
    assert B.to_ugml(10000.0, "nM", 117.15) == pytest.approx(1.1715)
    assert B.to_ugml(1.0, "uM", 500.0) == pytest.approx(0.5)            # 1 uM x 500 g/mol = 0.5 mg/L
    assert B.to_ugml(1.0, "nM", None) is None                           # molar with no MW: never guessed
    assert B.to_ugml(4.0, "pH units", 200.0) is None                    # not a concentration at all
    assert B.to_ugml(0.0, "ug.mL-1", None) is None and B.to_ugml(-1.0, "ug.mL-1", None) is None


def test_prepare_drops_only_the_unconvertible_rows(prepared):
    frame, report = prepared
    assert report["dropped_unconvertible_units"] == 1                   # the "pH units" row
    assert report["rows_out"] == 15
    assert "pH units" in report["units_dropped"]
    row = frame[(frame["molecule_chembl_id"] == "CHEMBL_D") & (frame["species"] == "Staphylococcus aureus")]
    assert row["mic_ugml"].iloc[0] == pytest.approx(1.1715)             # the nM row converted via full_mwt
    assert row["log_mic"].iloc[0] == pytest.approx(math.log10(1.1715))


# --- metrics -----------------------------------------------------------------------------------------------

def test_spearman_against_hand_computed_values():
    assert B.spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert B.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    # Monotone but not linear: Spearman is 1 where Pearson would not be.
    assert B.spearman([1, 2, 3, 4], [1, 10, 100, 1000]) == pytest.approx(1.0)
    # x = 1,2,3,4; y = 1,3,2,4 -> ranks differ in two adjacent places: rho = 1 - 6*sum(d^2)/(n(n^2-1))
    # d = 0,-1,1,0 -> sum d^2 = 2 -> rho = 1 - 12/60 = 0.8
    assert B.spearman([1, 2, 3, 4], [1, 3, 2, 4]) == pytest.approx(0.8)
    assert B.spearman([1, 2], [1, 2]) is None                           # too few points to mean anything
    assert B.spearman([1, 1, 1], [1, 2, 3]) is None                     # no variance to rank


def test_mae_against_hand_computed_values():
    assert B.mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0
    assert B.mae([0.0, 0.0, 0.0], [1.0, -2.0, 3.0]) == pytest.approx(2.0)   # (1+2+3)/3
    assert B.mae([], []) is None


def test_balanced_accuracy_against_hand_computed_values():
    # 8 negatives, 2 positives. Predict all negative: recall_0 = 1, recall_1 = 0 -> 0.5, where plain accuracy
    # would read 0.8. This is exactly why the metric is balanced.
    truth = [0] * 8 + [1] * 2
    assert B.balanced_accuracy(truth, [0] * 10) == pytest.approx(0.5)
    assert B.balanced_accuracy(truth, truth) == pytest.approx(1.0)
    # 6/8 negatives right, 1/2 positives right -> (0.75 + 0.5)/2 = 0.625
    assert B.balanced_accuracy(truth, [0, 0, 0, 0, 0, 0, 1, 1, 1, 0]) == pytest.approx(0.625)
    assert B.balanced_accuracy([1, 1, 1], [1, 1, 1]) is None            # one class only: undefined, not 1.0


# --- censoring ---------------------------------------------------------------------------------------------

def test_threshold_call_reads_a_censored_row_as_not_inhibited():
    frame = pd.DataFrame({"standard_relation": ["=", ">", ">=", "<"],
                          "log_mic": [math.log10(4), math.log10(128), math.log10(256), math.log10(64)],
                          "censored": [False, True, True, True]})
    # ">" and ">=" rows mean the bug grew at that concentration -> label 0; "=" and "<" mean it was inhibited -> 1.
    truth, predicted = B.threshold_labels(frame, [math.log10(4)] * 4)
    assert list(truth) == [1, 0, 0, 1]
    # A predicted MIC of 4 ug/mL is at or below every one of those concentrations, so every call is "inhibited".
    assert list(predicted) == [1, 1, 1, 1]
    truth, predicted = B.threshold_labels(frame, [math.log10(512)] * 4)
    assert list(predicted) == [0, 0, 0, 0]                              # 512 is above all four thresholds


def test_score_uses_exact_rows_for_regression_and_all_rows_for_the_threshold_call(prepared):
    frame, _ = prepared
    aureus = frame[frame["species"] == "Staphylococcus aureus"].reset_index(drop=True)
    scored = B.score(aureus, np.full(len(aureus), float(aureus["log_mic"].median())))
    assert scored["n_rows"] == len(aureus)
    assert scored["n_exact"] == int(((aureus["standard_relation"] == "=") & ~aureus["censored"]).sum())
    assert scored["n_censored"] == 1                                     # the "<" row
    assert scored["n_exact"] < scored["n_rows"]                          # the censored row is not in the Spearman
    assert scored["mae_log_mic"] >= 0


def test_score_ignores_rows_the_model_could_not_predict(prepared):
    frame, _ = prepared
    rows = frame.head(6).reset_index(drop=True)
    predictions = np.array([1.0, np.nan, 1.0, np.nan, 1.0, 1.0])
    assert B.score(rows, predictions)["n_rows"] == 4


# --- the baselines -----------------------------------------------------------------------------------------

def test_marginal_baseline_predicts_the_species_median_and_falls_back_globally(prepared):
    frame, _ = prepared
    train = frame[frame["species"] != "Bifidobacterium longum"]
    unseen = pd.DataFrame({"species": ["Staphylococcus aureus", "Bifidobacterium longum"]})
    predicted = B.marginal_predict(unseen, train)
    assert predicted[0] == pytest.approx(float(train[train["species"] == "Staphylococcus aureus"]
                                               ["log_mic"].median()))
    assert predicted[1] == pytest.approx(float(train["log_mic"].median()))   # held-out species: global median


def test_knn_uses_the_nearest_neighbour_measured_on_the_same_species(prepared):
    from screening.features import bitvects
    frame, _ = prepared
    fingerprints = bitvects(SMILES)
    coli = frame[frame["species"] == "Escherichia coli"]
    # CHEMBL_A (an ethoxy-benzamide) is far closer to CHEMBL_B (the matching acid) and CHEMBL_E (the N-methyl
    # amide) than to the dodecylamine or the indole, so its E. coli prediction must come from those relatives.
    held_out = coli[coli["molecule_chembl_id"] == "CHEMBL_A"].reset_index(drop=True)
    train = coli[coli["molecule_chembl_id"] != "CHEMBL_A"]
    predicted = B.knn_predict(held_out, train, fingerprints, k=1)
    assert predicted[0] == pytest.approx(float(train[train["molecule_chembl_id"] == "CHEMBL_B"]
                                               ["log_mic"].iloc[0]))
    assert np.isfinite(predicted).all()


def test_knn_has_no_opinion_without_a_neighbour_or_a_structure(prepared):
    from screening.features import bitvects
    frame, _ = prepared
    fingerprints = bitvects(SMILES)
    longum = frame[frame["species"] == "Bifidobacterium longum"].reset_index(drop=True)
    train = frame[frame["species"] != "Bifidobacterium longum"]
    # same_species=True and no train row on B. longum -> NaN, not a quietly borrowed number from another species.
    assert np.isnan(B.knn_predict(longum, train, fingerprints, k=5, same_species=True)).all()
    # Widening the neighbourhood is what cold_species does, and then it can answer.
    assert np.isfinite(B.knn_predict(longum, train, fingerprints, k=5, same_species=False)).all()
    # CHEMBL_H's SMILES does not parse, so it has no fingerprint and therefore no prediction.
    assert "CHEMBL_H" not in fingerprints


def test_evaluate_split_scores_both_baselines_on_the_same_rows(prepared, tmp_path):
    from screening.features import bitvects
    frame, _ = prepared
    S.generate(MATRIX, tmp_path, seed=S.SEED)
    split = S.Split.load("cold_compound", tmp_path)
    result = B.evaluate_split(frame, split, bitvects(SMILES), fold="test", k=1)
    assert result["aggregate"]["knn"]["n_rows"] == result["aggregate"]["marginal"]["n_rows"]
    assert result["knn_neighbourhood"] == "same species"
    assert 0.0 <= result["knn_coverage"] <= 1.0


def test_evaluate_split_handles_a_species_with_no_training_data(prepared, tmp_path):
    """The cold_species path end to end. Every held-out species has *zero* train rows by construction, so the
    stratification has to have a band for that - this is what caught `_tier_of` falling off the end of TIERS."""
    from screening.features import bitvects
    frame, _ = prepared
    S.generate(MATRIX, tmp_path, seed=S.SEED)
    split = S.Split.load("cold_species", tmp_path)
    result = B.evaluate_split(frame, split, bitvects(SMILES), fold="test", k=2)
    assert result["knn_neighbourhood"] == "all train species"    # same-species neighbours cannot exist here
    assert list(result["by_train_volume"]) == ["0"]
    assert result["aggregate"]["marginal"]["n_rows"] == result["aggregate"]["knn"]["n_rows"]


def test_tier_boundaries():
    # 0 has to be its own band: every cold_species holdout has no training data, and _tier_of must not fall
    # off the end of the list when it sees one.
    assert B._tier_of(0) == "0"
    assert B._tier_of(1) == "1-9" and B._tier_of(9) == "1-9"
    assert B._tier_of(10) == "10-99" and B._tier_of(99) == "10-99"
    assert B._tier_of(100) == "100-999" and B._tier_of(1000) == "1000+"
    assert B._tier_of(160257) == "1000+"
