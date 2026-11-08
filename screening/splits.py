"""The committed train/val/test splits over the MIC matrix, and the loader everything downstream must use.

    python -m screening.splits                      # write both split files from screening/data/mic_matrix.csv
    python -m screening.splits --show               # what is in the split files

    from screening.splits import Split, load_matrix
    split = Split.load("cold_compound")
    frame = load_matrix()
    train = split.subset(frame, "train")            # rows whose compound is in the train fold

**These files are the artifact, not the code that makes them.** A split regenerated per machine, even from the
same seed, drifts the moment pandas, Python's hash or the matrix changes by a row, and then two people's numbers
are no longer comparable. So each file carries the **explicit ID lists**, and whoever first builds the matrix
should generate them **once** and share them; nothing downstream may re-randomise. Each file records the seed, the
scoped row count and the matrix's sha256, so a mismatch is caught - as a warning, not a crash, because the matrix
changes whenever someone re-runs fetch_mic.py against a newer ChEMBL and the older split is still the one that any
published number was measured on.

Nothing in `screening/splits/` is committed today, because the matrix it would be cut from is not in the repo
either - see screening/README.md.

Two split kinds, because the screening stage has two different generalisation questions:

- **cold_compound** - every measurement of a compound lands in one fold (70/10/20 by compound). Answers "given a
  compound nobody has measured, can we predict its MIC on species we know?", which is the virtual-screening
  question: the candidate is new, the panel is not.
- **cold_species** - whole species are held out. Answers "can we predict on a species we have no data for?", which
  is the commensal-sparing question, and it is the hard one: gut commensals have 1,812 compound x species pairs
  against 245,556 for pathogens (DISCUSSIONS.md, "Antimicrobial re-framing: data check"), so a model that only
  interpolates within a species will score well on cold_compound and be useless for what we actually want.
"""
import argparse
import gzip
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parent / "data"
SPLITS = Path(__file__).resolve().parent / "splits"


def data_path(folder: Path = FOLDER) -> Path:
    """The MIC matrix: the plain CSV a fetch leaves behind, else the committed `.csv.gz`.

    The raw CSV is ~96 MB, which is past what this repo commits (CONTRIBUTING.md), so what is committed is the
    gzip - a quarter of the size and the identical table. pandas reads either, and `sha256()` hashes the
    *decompressed* bytes so a split cut from one form validates against the other.
    """
    plain = folder / "mic_matrix.csv"
    return plain if plain.exists() else folder / "mic_matrix.csv.gz"


DATA = data_path()

SEED = 20261108                 # the date this was first generated; any fixed number would do, this one is a note
FRACTIONS = {"train": 0.7, "val": 0.1, "test": 0.2}

# The commensal we are trying to spare and the pathogens we are trying to hit: the panel agreed for the downstream
# OT-2 MIC run (DISCUSSIONS.md). Held here as the canonical IDs so splits.py, features.py and baseline.py name the
# same four species.
PANEL = {"CHEMBL614965": "Clostridioides difficile", "CHEMBL362": "Enterococcus faecalis",
         "CHEMBL614411": "Bacteroides fragilis", "CHEMBL613911": "Bifidobacterium longum"}

# Bifidobacterium longum is held out by requirement - it is the commensal arm of the panel, and a model that
# cannot speak about it cannot answer the question the project is asking. The rest are chosen in
# `choose_holdouts()` from the data, because "enough data to be measurable" is a property of the matrix.
REQUIRED_TEST_SPECIES = ["Bifidobacterium longum"]

# An epithet is lowercase and alphabetic; a strain or serovar token is not ("H37Rv", "O157:H7", "ATCC").
_EPITHET = re.compile(r"^[a-z]+$")


def species_key(organism: str | None) -> str:
    """ChEMBL's free-text organism name reduced to a genus + species binomial.

    ChEMBL is species-level anyway (only 10 of 2,784 organism targets are strain-resolved; strain IDs live in assay
    free text), but the *names* are not normalised: "Mycobacterium tuberculosis H37Rv", "Staphylococcus aureus
    subsp. aureus" and "Staphylococcus aureus" are three strings for two species. Holding out a species has to mean
    holding out every spelling of it, or the held-out data leaks back in under another name.
    """
    tokens = (organism or "").strip().split()
    if len(tokens) >= 2 and _EPITHET.match(tokens[1]):
        return f"{tokens[0]} {tokens[1]}"
    return " ".join(tokens)


def load_matrix(path: Path | str = DATA, scope: bool = True) -> pd.DataFrame:
    """The MIC matrix with `species` (the normalised binomial) and `censored` as a real bool.

    `scope=True` keeps only rows that can carry a prediction: a compound, a named organism and a numeric value.
    Everything in this folder - splits, features, baselines - works on the scoped frame, so the denominators match.
    """
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame["censored"] = frame["censored"].str.lower().isin({"true", "1"})
    frame["value"] = pd.to_numeric(frame["standard_value"], errors="coerce")
    frame["species"] = [species_key(o) for o in frame["target_organism"]]
    if scope:
        frame = frame[(frame["molecule_chembl_id"] != "") & (frame["species"] != "") & frame["value"].notna()]
    return frame.reset_index(drop=True)


def sha256(path: Path) -> str:
    """Hash of the table's *content*, so mic_matrix.csv and mic_matrix.csv.gz give the same digest."""
    path = Path(path)
    digest = hashlib.sha256()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --- the loader --------------------------------------------------------------------------------------------

@dataclass
class Split:
    """A committed split: a mapping from one ID (a compound or a species) to a fold. Read-only on purpose."""
    name: str
    unit: str                                        # the column the IDs are values of
    ids: dict[str, list[str]]                        # fold -> IDs
    meta: dict

    @classmethod
    def load(cls, name: str, folder: Path | str = SPLITS) -> "Split":
        spec = json.loads((Path(folder) / f"{name}.json").read_text())
        return cls(spec["name"], spec["unit"], {f: list(v) for f, v in spec["ids"].items()}, spec)

    @property
    def folds(self) -> list[str]:
        return list(self.ids)

    def fold_of(self, key: str) -> str | None:
        """The fold an ID belongs to, or None when the split does not mention it (a cold_species split names only
        the species it holds out plus the train pool, so an unseen species is honestly None)."""
        return self._index().get(key)

    def _index(self) -> dict[str, str]:
        if not hasattr(self, "_lookup"):
            self._lookup = {key: fold for fold, keys in self.ids.items() for key in keys}
        return self._lookup

    def assign(self, frame: pd.DataFrame) -> pd.Series:
        """The fold of every row (NA where the split does not place it)."""
        return frame[self.unit].map(self._index())

    def subset(self, frame: pd.DataFrame, fold: str) -> pd.DataFrame:
        if fold not in self.ids:
            raise KeyError(f"{self.name} has no fold {fold!r} (folds: {self.folds})")
        return frame[self.assign(frame) == fold]

    def check_matrix(self, path: Path | str = DATA) -> list[str]:
        """Warnings if the matrix is not the one the split was cut from. Deliberately not an exception: the matrix
        grows every time someone re-runs fetch_mic.py, and the committed split stays the comparable one."""
        source, warnings = self.meta.get("source", {}), []
        path = Path(path)
        if not path.exists():
            return [f"{path} is missing"]
        if source.get("sha256") and source["sha256"] != sha256(path):
            warnings.append(f"{path.name} is not the file {self.name} was cut from "
                            f"(expected {source.get('scoped_rows')} scoped rows from sha256 "
                            f"{source['sha256'][:12]}...); "
                            "the committed split is still the comparable one")
        return warnings


# --- generating the splits ---------------------------------------------------------------------------------

def _source(path: Path, frame: pd.DataFrame) -> dict:
    return {"file": f"screening/data/{path.name}", "scoped_rows": int(len(frame)), "sha256": sha256(path),
            "compounds": int(frame["molecule_chembl_id"].nunique()),
            "species": int(frame["species"].nunique())}


def _write(spec: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{spec['name']}.json"
    path.write_text(json.dumps(spec, indent=1, sort_keys=False) + "\n")
    print(f"wrote {path} ({', '.join(f'{f}={len(v)}' for f, v in spec['ids'].items())})")
    return path


def cold_compound(frame: pd.DataFrame, path: Path = DATA, seed: int = SEED,
                  fractions: dict[str, float] | None = None) -> dict:
    """Every measurement of a compound in one fold. Shuffled from a sorted list so the seed alone fixes it."""
    fractions = fractions or FRACTIONS
    compounds = sorted(frame["molecule_chembl_id"].unique())
    random.Random(seed).shuffle(compounds)
    n_train = int(len(compounds) * fractions["train"])
    n_val = int(len(compounds) * fractions["val"])
    ids = {"train": sorted(compounds[:n_train]), "val": sorted(compounds[n_train:n_train + n_val]),
           "test": sorted(compounds[n_train + n_val:])}
    rows = {fold: int(frame["molecule_chembl_id"].isin(set(keys)).sum()) for fold, keys in ids.items()}
    return {"name": "cold_compound", "unit": "molecule_chembl_id", "seed": seed,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": _source(path, frame),
            "question": "a compound nobody has measured, on species we have data for (the screening case)",
            "fractions": fractions, "row_counts": rows,
            "note": "shuffle of the sorted compound list under `seed`; regenerating changes every reported number",
            "ids": ids}


def bacteria(table: pd.DataFrame | None) -> set[str] | None:
    """The species in a `features.species_features()` table that ChEMBL classifies as Bacteria, or None.

    None means "no taxonomy was supplied", which the callers treat as "do not filter by kingdom" and record.
    """
    if table is None or "chembl_l1" not in table.columns:
        return None
    return set(table.loc[table["chembl_l1"] == "Bacteria", "species"])


def choose_holdouts(frame: pd.DataFrame, n_extra: int = 3, min_rows: int = 150, min_compounds: int = 60,
                    only: set[str] | None = None) -> tuple[list[str], list[dict]]:
    """Species to hold out as cold_species test: the required ones plus `n_extra` chosen from the data.

    "Enough data to be measurable" is the whole constraint. A held-out species with 9 measurements gives a Spearman
    with no meaning, so an extra holdout needs >= `min_rows` rows and >= `min_compounds` distinct compounds. Among
    those we take the ones nearest the **median** of the eligible species by row count rather than the largest:
    holding out Staphylococcus aureus would remove a tenth of the training data and measure generalisation to a
    species unlike anything left, while a mid-sized species leaves the training pool intact and is the realistic
    case - a species somebody has looked at a little, which is what a new panel member looks like.

    `only` restricts the extras to a set of species - in practice `bacteria(species_features())`. It matters: run
    without it on the real matrix, the mid-sized band is full of *fungi* (Penicillium chrysogenum, Lichtheimia
    corymbifera, Trichoderma viride), because ChEMBL's MIC rows include antifungal assays. Holding those out would
    measure generalisation across kingdoms, which is not the question this stage asks.
    """
    per_species = frame.groupby("species").agg(rows=("value", "size"),
                                               compounds=("molecule_chembl_id", "nunique")).sort_values("rows")
    rationale = []
    for name in REQUIRED_TEST_SPECIES:
        stats = per_species.loc[name] if name in per_species.index else None
        rationale.append({"species": name, "rows": int(stats["rows"]) if stats is not None else 0,
                          "compounds": int(stats["compounds"]) if stats is not None else 0,
                          "why": "required: the commensal arm of the downstream OT-2 panel, and the species the "
                                 "commensal-sparing question is about. Sparse on purpose - this is the hard case."})
    eligible = per_species[(per_species["rows"] >= min_rows) & (per_species["compounds"] >= min_compounds)]
    eligible = eligible.drop(index=[s for s in REQUIRED_TEST_SPECIES if s in eligible.index])
    if only is not None:
        eligible = eligible[eligible.index.isin(only)]
    if eligible.empty:
        return list(REQUIRED_TEST_SPECIES), rationale
    # Nearest the median row count, taking the larger side first so the picks stay comfortably measurable.
    median = eligible["rows"].median()
    order = (eligible["rows"] - median).abs().sort_values(kind="stable").index
    extra = list(order[:n_extra])
    for name in extra:
        stats = eligible.loc[name]
        rationale.append({"species": name, "rows": int(stats["rows"]), "compounds": int(stats["compounds"]),
                          "why": f"mid-sized species ({int(stats['rows'])} rows, {int(stats['compounds'])} "
                                 f"compounds, against a median of {int(median)} among the "
                                 f"{len(eligible)} species with >= {min_rows} rows and >= {min_compounds} "
                                 "compounds): measurable without stripping the training pool"})
    return list(REQUIRED_TEST_SPECIES) + extra, rationale


def cold_species(frame: pd.DataFrame, path: Path = DATA, seed: int = SEED, n_extra: int = 3, n_val: int = 3,
                 only: set[str] | None = None) -> dict:
    """Whole species held out. Test = the chosen holdouts; val = `n_val` more (for model selection, so nothing is
    tuned on test); train = every other species."""
    test, rationale = choose_holdouts(frame, n_extra=n_extra, only=only)
    per_species = frame.groupby("species").agg(rows=("value", "size"),
                                               compounds=("molecule_chembl_id", "nunique"))
    remaining = per_species.drop(index=[s for s in test if s in per_species.index])
    # Val species are picked the same way as the test extras, so the two are comparable in size.
    pool = remaining[(remaining["rows"] >= 150) & (remaining["compounds"] >= 60)]
    if only is not None:
        pool = pool[pool.index.isin(only)]
    median = pool["rows"].median() if not pool.empty else 0
    val = list((pool["rows"] - median).abs().sort_values(kind="stable").index[:n_val])
    train = sorted(set(per_species.index) - set(test) - set(val))
    ids = {"train": train, "val": sorted(val), "test": sorted(test)}
    rows = {fold: int(frame["species"].isin(set(keys)).sum()) for fold, keys in ids.items()}
    return {"name": "cold_species", "unit": "species", "seed": seed,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": _source(path, frame),
            "question": "a species we have no MIC data for (the commensal-sparing case)",
            "row_counts": rows, "test_rationale": rationale,
            "restricted_to_bacteria": only is not None,
            "warning": None if only is not None else
            "no taxonomy was supplied, so the extra holdouts are NOT restricted to bacteria - run "
            "`python -m screening.features --species` first, or check the picks by hand",
            "note": "`species` is screening.splits.species_key(target_organism): a species is held out under every "
                    "spelling of its name, strains and subspecies included",
            "panel": PANEL, "ids": ids}


def generate(path: Path = DATA, folder: Path = SPLITS, seed: int = SEED,
             taxonomy: pd.DataFrame | None = None) -> dict[str, Path]:
    """Both splits. `taxonomy` is a `features.species_features()` table; without one the cold_species holdouts
    are not restricted to bacteria and the written file says so."""
    frame = load_matrix(path)
    print(f"{len(frame)} scoped rows, {frame['molecule_chembl_id'].nunique()} compounds, "
          f"{frame['species'].nunique()} species")
    only = bacteria(taxonomy)
    if only is None:
        print("  no species table: cold_species holdouts are not restricted to bacteria (see the file's warning)")
    return {spec["name"]: _write(spec, folder)
            for spec in (cold_compound(frame, path, seed), cold_species(frame, path, seed, only=only))}


def show(folder: Path = SPLITS) -> None:
    for path in sorted(Path(folder).glob("*.json")):
        split = Split.load(path.stem, folder)
        print(f"\n{split.name}: unit={split.unit} seed={split.meta['seed']} "
              f"cut from {split.meta['source']['scoped_rows']} rows ({split.meta['generated_utc']})")
        for fold, keys in split.ids.items():
            rows = split.meta["row_counts"][fold]
            head = ", ".join(keys[:4]) + (" ..." if len(keys) > 4 else "")
            print(f"  {fold:5s} {len(keys):7d} {split.unit}  {rows:8d} rows   {head}")
        for item in split.meta.get("test_rationale", []):
            print(f"  held out: {item['species']} ({item['rows']} rows, {item['compounds']} compounds)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--folder", type=Path, default=SPLITS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--show", action="store_true", help="print the split files instead of regenerating them")
    args = parser.parse_args()
    if args.show:
        show(args.folder)
        return
    # Imported here, not at module scope: features.py reads this module, and splits.py works without a species
    # table (it just cannot restrict the holdouts to bacteria, which the written file then warns about).
    try:
        from screening.features import species_features
        taxonomy = species_features()
    except (ImportError, FileNotFoundError):
        taxonomy = None
    generate(args.data, args.folder, args.seed, taxonomy)


if __name__ == "__main__":
    main()
