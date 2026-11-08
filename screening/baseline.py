"""Two baselines on the committed splits -> screening/results/baseline.json.

    python -m screening.baseline                     # both splits, both baselines
    python -m screening.baseline --split cold_species --k 5

    (a) **kNN on chemistry** - a compound's MIC on a species is the median of its nearest ECFP4 neighbours
        measured on that same species (cold_compound). For cold_species there are no neighbours on the held-out
        species by construction, so the neighbourhood widens to every train species and the number it gives is the
        honest answer to "what does chemistry alone know about a species you have never measured?".
    (b) **species-marginal** - the species' median MIC, ignoring chemistry entirely. For a held-out species there
        is no median either, so it falls back to the global train median.

**(b) existing is the point.** The marginal baseline is what you get for free from knowing which bug you are
testing, and antimicrobial potency is dominated by the species: a compound ranked against S. aureus is being
ranked against a species whose MICs sit decades away from Bacteroides fragilis's. If the kNN does not beat the
marginal, the chemistry is contributing nothing and a fancier model is not the fix - the data is.

Metrics, per split, aggregate **and stratified by how much data each species has** (a Spearman averaged over
S. aureus and a 30-row species says nothing about either):

- **Spearman** and **MAE** on log10 MIC, over uncensored `=` rows only - those are the only rows with a value.
- **Balanced accuracy** over a threshold call, which is how the censored rows earn their keep: a row reading
  ">128 ug/mL" says "not inhibited at 128", a row reading "= 4" says "inhibited at 4", and a prediction is scored
  on whether it gets that call right at that row's own concentration. Balanced rather than plain accuracy because
  the two classes are nowhere near even.

MIC values arrive in ug.mL-1 (81%) and in molar units; everything is converted to **ug/mL** using ChEMBL's
`full_mwt` from the SMILES cache, and a row whose units cannot be converted is dropped with a count, never guessed.
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import DataStructs

from screening.features import SMILES_CACHE, bitvects, smiles_table
from screening.splits import DATA, PANEL, SPLITS, Split, load_matrix

RESULTS = Path(__file__).resolve().parent / "results" / "baseline.json"

K = 5                           # neighbours; a median over 5 is robust without needing a dense neighbourhood
SEED = 20261108                 # only used by the per-species evaluation cap, and recorded in the results file
MAX_EVAL_ROWS_PER_SPECIES = 2000

# Mass concentrations convert straight to ug/mL; molar ones need the molecular weight (factor x MW).
MASS_TO_UGML = {"ug.mL-1": 1.0, "mg.mL-1": 1e3, "ng.mL-1": 1e-3, "mg L-1": 1.0, "ug L-1": 1e-3,
                "g.L-1": 1e3, "mg/L": 1.0, "ug/ml": 1.0}
MOLAR_TO_UGML_PER_MWT = {"M": 1e3, "mM": 1.0, "uM": 1e-3, "nM": 1e-6, "pM": 1e-9, "fM": 1e-12}

# How much data a species has, which is the axis every number here is stratified along. The bands are
# order-of-magnitude, which is the resolution the asymmetry actually has (245,556 pathogen pairs against 1,812
# commensal ones, DISCUSSIONS.md).
# The "0" band is not a rounding artefact: it is every species cold_species holds out, which has no training data
# by construction, and it is the band the commensal question actually lives in.
TIERS = [("0", 0, 1), ("1-9", 1, 10), ("10-99", 10, 100), ("100-999", 100, 1000), ("1000+", 1000, math.inf)]

# Relations that mean "we never saw inhibition up to this concentration".
NOT_INHIBITED = {">", ">="}


# --- the target variable -----------------------------------------------------------------------------------

def to_ugml(value: float, units: str, mwt: float | None) -> float | None:
    """A MIC in ug/mL, or None when the units are unknown or a molar value has no molecular weight."""
    if value is None or not np.isfinite(value) or value <= 0:
        return None                                          # log10 of a zero or negative MIC means nothing
    units = (units or "").strip()
    if units in MASS_TO_UGML:
        return value * MASS_TO_UGML[units]
    if units in MOLAR_TO_UGML_PER_MWT:
        if mwt is None or not np.isfinite(mwt) or mwt <= 0:
            return None
        return value * MOLAR_TO_UGML_PER_MWT[units] * mwt
    return None


def prepare(frame: pd.DataFrame, cache_path: Path = SMILES_CACHE) -> tuple[pd.DataFrame, dict]:
    """Add `mic_ugml` and `log_mic` to the scoped matrix, dropping rows whose units cannot be converted."""
    weights = smiles_table(cache_path).set_index("molecule_chembl_id")["full_mwt"].to_dict()
    mwt = frame["molecule_chembl_id"].map(weights)
    converted = [to_ugml(v, u, w) for v, u, w in zip(frame["value"], frame["standard_units"], mwt)]
    frame = frame.assign(mic_ugml=converted)
    dropped = frame["mic_ugml"].isna()
    report = {"rows_in": int(len(frame)), "dropped_unconvertible_units": int(dropped.sum()),
              "units_dropped": frame.loc[dropped, "standard_units"].value_counts().head(8).to_dict()}
    frame = frame[~dropped].copy()
    frame["log_mic"] = np.log10(frame["mic_ugml"])
    report["rows_out"] = int(len(frame))
    return frame, report


# --- metrics (no scipy in this env, so Spearman is ranks + Pearson) ----------------------------------------

def spearman(a, b) -> float | None:
    """Spearman rho = Pearson on the ranks. None when there is nothing to correlate (<3 points, or no variance)."""
    a, b = pd.Series(list(a), dtype=float), pd.Series(list(b), dtype=float)
    if len(a) < 3:
        return None
    ranked_a, ranked_b = a.rank(), b.rank()
    if ranked_a.std() == 0 or ranked_b.std() == 0:
        return None
    return float(np.corrcoef(ranked_a, ranked_b)[0, 1])


def mae(a, b) -> float | None:
    a, b = np.asarray(list(a), dtype=float), np.asarray(list(b), dtype=float)
    return float(np.mean(np.abs(a - b))) if len(a) else None


def balanced_accuracy(y_true, y_pred) -> float | None:
    """Mean of the two per-class recalls. None unless both classes are present (one class makes it meaningless)."""
    y_true, y_pred = np.asarray(list(y_true), dtype=int), np.asarray(list(y_pred), dtype=int)
    recalls = [float((y_pred[y_true == c] == c).mean()) for c in (0, 1) if (y_true == c).any()]
    return float(np.mean(recalls)) if len(recalls) == 2 else None


def threshold_labels(frame: pd.DataFrame, predictions) -> tuple[np.ndarray, np.ndarray]:
    """The threshold call for every row: was the compound inhibitory at the concentration this row reports?

    A `>`/`>=` row is a 0 (it grew at that concentration); anything else is a 1 (it was inhibited at or below it).
    The prediction makes the same call by asking whether the predicted MIC is at or under that concentration.
    """
    truth = (~frame["standard_relation"].isin(NOT_INHIBITED)).astype(int).to_numpy()
    predicted = (np.asarray(predictions, dtype=float) <= frame["log_mic"].to_numpy()).astype(int)
    return truth, predicted


def score(frame: pd.DataFrame, predictions) -> dict:
    """Spearman + MAE over the uncensored `=` rows, balanced accuracy over all rows as a threshold call."""
    predictions = np.asarray(predictions, dtype=float)
    keep = np.isfinite(predictions)
    frame, predictions = frame[keep], predictions[keep]
    exact = (frame["standard_relation"] == "=") & ~frame["censored"]
    truth, predicted = threshold_labels(frame, predictions)
    return {"n_rows": int(len(frame)), "n_exact": int(exact.sum()), "n_censored": int(frame["censored"].sum()),
            "spearman_log_mic": spearman(frame.loc[exact, "log_mic"], predictions[exact.to_numpy()]),
            "mae_log_mic": mae(frame.loc[exact, "log_mic"], predictions[exact.to_numpy()]),
            "balanced_accuracy_threshold": balanced_accuracy(truth, predicted)}


# --- the baselines -----------------------------------------------------------------------------------------

def _per_compound_species(train: pd.DataFrame) -> pd.DataFrame:
    """One log10 MIC per (compound, species): the median of its replicates, so a compound measured 40 times in one
    paper does not outvote 40 compounds."""
    return (train.groupby(["species", "molecule_chembl_id"])["log_mic"].median().reset_index())


def marginal_predict(evaluate: pd.DataFrame, train: pd.DataFrame) -> np.ndarray:
    """(b) the species' median log10 MIC, ignoring the compound. Global train median where the species is unseen."""
    medians = train.groupby("species")["log_mic"].median()
    overall = float(train["log_mic"].median())
    return evaluate["species"].map(medians).fillna(overall).to_numpy(dtype=float)


def knn_predict(evaluate: pd.DataFrame, train: pd.DataFrame, fingerprints: dict, k: int = K,
                same_species: bool = True) -> np.ndarray:
    """(a) median log10 MIC of the k nearest ECFP4 neighbours; NaN where a row has no neighbour at all.

    `same_species=True` restricts the neighbourhood to compounds measured on the row's own species (cold_compound);
    False pools every train species (cold_species, where the row's species has no train data by construction).
    """
    folded = _per_compound_species(train)
    predictions = np.full(len(evaluate), np.nan)

    def neighbourhood(pool: pd.DataFrame) -> tuple[list, np.ndarray]:
        pool = pool[pool["molecule_chembl_id"].isin(fingerprints)]
        return ([fingerprints[m] for m in pool["molecule_chembl_id"]], pool["log_mic"].to_numpy(dtype=float))

    # The pooled neighbourhood is one row per *compound* (its median log10 MIC over every train species), not one
    # per compound x species. Both because it is the sensible reading of "this compound's typical MIC" and because
    # the per-pair version would put a compound measured on 40 species into the neighbourhood 40 times - and make
    # the pass 2.5x longer for the same answer.
    pooled = None if same_species else neighbourhood(
        train.groupby("molecule_chembl_id")["log_mic"].median().reset_index())
    for species, group in evaluate.groupby("species", sort=False):
        vectors, values = pooled if pooled is not None else neighbourhood(folded[folded["species"] == species])
        if not vectors:
            continue                                         # no train compound to lean on: leave NaN, report it
        # One similarity pass per *unique* compound in the group, reused across its replicate rows.
        for molecule_id, rows in group.groupby("molecule_chembl_id", sort=False):
            query = fingerprints.get(molecule_id)
            if query is None:
                continue                                     # no structure, so no chemistry-based prediction
            similarity = np.asarray(DataStructs.BulkTanimotoSimilarity(query, vectors))
            top = np.argpartition(-similarity, min(k, len(similarity) - 1))[:k] if len(similarity) > k \
                else np.arange(len(similarity))
            predictions[evaluate.index.get_indexer(rows.index)] = float(np.median(values[top]))
    return predictions


# --- evaluation --------------------------------------------------------------------------------------------

def _cap(frame: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    """At most `limit` evaluation rows per species, sampled deterministically.

    A runtime cap, not a statistical choice: S. aureus alone has 160k MIC rows and the kNN is O(eval x train).
    Recorded in the results file so the number is reproducible and the cap is visible."""
    if limit <= 0 or frame.empty:
        return frame
    sizes = frame.groupby("species")["log_mic"].transform("size")
    over = frame[sizes > limit]
    if over.empty:
        return frame
    sampled = over.groupby("species", group_keys=False).sample(n=limit, random_state=seed)
    return pd.concat([frame[sizes <= limit], sampled]).sort_index()


def _tier_of(n_rows: int) -> str:
    return next(name for name, low, high in TIERS if low <= n_rows < high)


def evaluate_split(frame: pd.DataFrame, split: Split, fingerprints: dict, fold: str = "test", k: int = K,
                   cap: int = MAX_EVAL_ROWS_PER_SPECIES, seed: int = SEED) -> dict:
    """Both baselines on one fold of one split, aggregate and stratified by the species' training volume."""
    train = frame[split.assign(frame) == "train"]
    evaluate = _cap(split.subset(frame, fold), cap, seed).reset_index(drop=True)
    same_species = split.unit != "species"                   # a held-out species has no same-species neighbours
    train_rows = train.groupby("species")["log_mic"].size().to_dict()

    predicted = {"knn": knn_predict(evaluate, train, fingerprints, k=k, same_species=same_species),
                 "marginal": marginal_predict(evaluate, train)}
    # Both baselines are scored on exactly the rows the kNN can speak about, so the comparison is like for like;
    # `knn_coverage` says how many rows that left out.
    covered = np.isfinite(predicted["knn"])
    comparable = evaluate[covered].reset_index(drop=True)

    result = {"fold": fold, "n_eval_rows": int(len(evaluate)), "eval_rows_capped_per_species": cap,
              "cap_seed": seed, "knn_neighbourhood": "same species" if same_species else "all train species",
              "k": k, "train_rows": int(len(train)),
              "knn_coverage": round(float(covered.mean()), 4) if len(evaluate) else None,
              "scored_rows": int(len(comparable)),
              "aggregate": {name: score(comparable, values[covered]) for name, values in predicted.items()}}

    tier = comparable["species"].map(lambda s: _tier_of(train_rows.get(s, 0)))
    result["by_train_volume"] = {
        name: {model: score(comparable[tier == name], values[covered][(tier == name).to_numpy()])
               for model, values in predicted.items()}
        for name in dict.fromkeys(tier) if (tier == name).any()}
    result["by_panel_species"] = {
        species: {"train_rows": int(train_rows.get(species, 0)),
                  **{model: score(comparable[comparable["species"] == species],
                                  values[covered][(comparable["species"] == species).to_numpy()])
                     for model, values in predicted.items()}}
        for species in sorted(set(PANEL.values())) if (comparable["species"] == species).any()}
    return result


def run(data: Path = DATA, splits_folder: Path = SPLITS, out: Path = RESULTS, k: int = K,
        names: list[str] | None = None, cap: int = MAX_EVAL_ROWS_PER_SPECIES) -> dict:
    frame, units = prepare(load_matrix(data))
    print(f"{units['rows_out']} rows with a MIC in ug/mL "
          f"({units['dropped_unconvertible_units']} dropped on units)")
    names = names or ["cold_compound", "cold_species"]
    loaded = {name: Split.load(name, splits_folder) for name in names}
    for split in loaded.values():
        for warning in split.check_matrix(data):
            print(f"  warning: {warning}")

    fingerprints = bitvects(ids=sorted(frame["molecule_chembl_id"].unique()))
    print(f"{len(fingerprints)} ECFP4 fingerprints")

    results = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "matrix": {"file": f"screening/data/{Path(data).name}", **units},
               "baselines": {"knn": "median log10 MIC of the k nearest ECFP4 neighbours",
                             "marginal": "the species' median log10 MIC, chemistry ignored"},
               "splits": {}}
    for name, split in loaded.items():
        print(f"\n{name}:")
        results["splits"][name] = evaluate_split(frame, split, fingerprints, k=k, cap=cap)
        for model, scored in results["splits"][name]["aggregate"].items():
            print(f"  {model:9s} spearman={scored['spearman_log_mic']} mae={scored['mae_log_mic']} "
                  f"balanced_acc={scored['balanced_accuracy_threshold']} (n_exact={scored['n_exact']})")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"\nwrote {out}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--splits", type=Path, default=SPLITS)
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--k", type=int, default=K)
    parser.add_argument("--cap", type=int, default=MAX_EVAL_ROWS_PER_SPECIES,
                        help="max evaluation rows per species (0 = no cap)")
    parser.add_argument("--split", action="append", dest="names", help="only this split (repeatable)")
    args = parser.parse_args()
    run(args.data, args.splits, args.out, k=args.k, names=args.names, cap=args.cap)


if __name__ == "__main__":
    main()
