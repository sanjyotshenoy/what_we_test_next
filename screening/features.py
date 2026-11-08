"""Features for the screening stage: ECFP4 fingerprints per compound, and what ChEMBL knows about each species.

    python -m screening.features --smiles            # fetch + cache SMILES for every compound in the matrix
    python -m screening.features --species           # build screening/data/species_features.csv
    python -m screening.features                     # both, then the fingerprint matrix

    from screening.features import fingerprints, species_features
    ids, bits = fingerprints()                       # ids[i] <-> bits[i], 2048-bit ECFP4, uint8 0/1
    species_features()                               # one row per species, with ChEMBL's own taxonomy

**Compounds.** ECFP4 (Morgan radius 2, 2048 bits) from the canonical SMILES. SMILES come from ChEMBL's molecule
endpoint in batches of 100 and are cached in `data/smiles.csv.gz` (committed, so nobody has to re-download them);
`full_mwt` is cached alongside, because MIC values arrive in ug.mL-1 *and* in nM and converting between them needs
a molecular weight (baseline.py does the conversion).

**Species.** Only what ChEMBL and NCBI taxonomy actually say: the organism name, its NCBI `tax_id`, the genus read
off the binomial, and ChEMBL's own three-level organism classification - `l1` a kingdom-ish bucket (Bacteria,
Eukaryotes), `l2` which for bacteria is **Gram-Negative / Gram-Positive**, `l3` a genus-level group. That l2 is
ChEMBL's curation, not our inference, which is why it is allowed to be a feature here.

TODO(final): genotype features are the intended next addition and the thing most likely to make cold_species work
- presence of a homolog of the compound's target in the species' genome, known resistance genes (beta-lactamases,
efflux pumps), and a Gram stain / cell-envelope call that does not come from ChEMBL's l2 bucket. They need a
genome source (NCBI assembly or a curated table), so they are deliberately absent rather than guessed: a made-up
genotype feature would make cold_species look solved while predicting nothing. `species_genotype_features()` is
the hook they plug into; it returns an empty dict today and every caller already handles that.
"""
import argparse
import csv
import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator

from screening.fetch_mic import TIMEOUT_S, fetch_page  # noqa: F401  (fetch_page: same retry policy, same service)
from screening.splits import DATA, load_matrix, species_key

API = "https://www.ebi.ac.uk/chembl/api/data"
BATCH = 100                     # `__in` batches; 100 ids per request answers in ~1s
DELAY_S = 0.1

FOLDER = Path(__file__).resolve().parent / "data"
SMILES_CACHE = FOLDER / "smiles.csv.gz"
SPECIES_CSV = FOLDER / "species_features.csv"
FINGERPRINTS = FOLDER / "ecfp4.npz"

RADIUS, N_BITS = 2, 2048        # ECFP4 = Morgan radius 2; 2048 bits is the usual size for this kind of screen

RDLogger.DisableLog("rdApp.*")  # a few hundred of ChEMBL's SMILES do not parse; we count them instead
_GENERATOR = rdFingerprintGenerator.GetMorganGenerator(radius=RADIUS, fpSize=N_BITS)


# --- compounds ---------------------------------------------------------------------------------------------

def ecfp4(smiles: str) -> np.ndarray | None:
    """A 2048-bit ECFP4 as a uint8 0/1 vector, or None when RDKit cannot parse the SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return np.frombuffer(_GENERATOR.GetFingerprintAsNumPy(mol).astype(np.uint8).tobytes(), dtype=np.uint8)


def tanimoto(bits: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Tanimoto of one fingerprint against every row of `matrix`, as float64."""
    intersection = matrix.astype(np.int32) @ bits.astype(np.int32)
    union = matrix.sum(axis=1) + bits.sum() - intersection
    return np.divide(intersection, union, out=np.zeros(len(matrix), dtype=float), where=union > 0)


def ecfp4_bitvect(smiles: str):
    """The same ECFP4 as `ecfp4`, as an RDKit ExplicitBitVect.

    Two representations of one fingerprint, on purpose: the numpy matrix is what a model wants, and the bit vector
    is what `DataStructs.BulkTanimotoSimilarity` wants. The kNN baseline compares millions of pairs, and the
    numpy route would need a dense float matrix of every train compound (300+ MB for Staphylococcus aureus alone);
    RDKit does it in C++ over packed bits.
    """
    mol = Chem.MolFromSmiles(smiles)
    return None if mol is None else _GENERATOR.GetFingerprint(mol)


def bitvects(cache_path: Path = SMILES_CACHE, ids: list[str] | None = None) -> dict:
    """molecule_chembl_id -> ExplicitBitVect, built straight from the committed SMILES cache (~1 min for 115k)."""
    frame = smiles_table(cache_path)
    frame = frame[frame["canonical_smiles"] != ""]
    if ids is not None:
        frame = frame[frame["molecule_chembl_id"].isin(set(ids))]
    found = {}
    for molecule_id, smiles in zip(frame["molecule_chembl_id"], frame["canonical_smiles"]):
        fingerprint = ecfp4_bitvect(smiles)
        if fingerprint is not None:
            found[molecule_id] = fingerprint
    return found


def _get(path: str, params: dict, max_retries: int = 6) -> dict:
    """One GET against the ChEMBL API with the same backoff policy as fetch_mic.fetch_page."""
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(max_retries):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                           "User-Agent": "wwtn-screening/0.1 (biohack)"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                return json.loads(response.read())
        except Exception:                                    # noqa: BLE001 - any transport failure is retryable
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def _read_smiles_cache(path: Path = SMILES_CACHE) -> dict[str, dict]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return {r["molecule_chembl_id"]: r for r in frame.to_dict("records")}


def _write_smiles_cache(cache: dict[str, dict], path: Path = SMILES_CACHE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["molecule_chembl_id", "canonical_smiles", "full_mwt"])
        writer.writeheader()
        for key in sorted(cache):
            writer.writerow({k: cache[key].get(k, "") for k in writer.fieldnames})


def fetch_smiles(ids: list[str], path: Path = SMILES_CACHE, batch: int = BATCH,
                 delay_s: float = DELAY_S) -> dict[str, dict]:
    """Cache canonical SMILES and full_mwt for `ids`. Only the missing ones are fetched, so this is restartable
    and cheap to re-run; the cache is flushed every 50 batches so an interrupted run keeps its progress."""
    cache = _read_smiles_cache(path)
    missing = [i for i in dict.fromkeys(ids) if i and i not in cache]
    print(f"{len(cache)} cached, {len(missing)} to fetch")
    for number, start in enumerate(range(0, len(missing), batch), start=1):
        chunk = missing[start:start + batch]
        payload = _get("molecule.json", {"molecule_chembl_id__in": ",".join(chunk), "limit": batch})
        for molecule in payload.get("molecules", []):
            structures = molecule.get("molecule_structures") or {}
            properties = molecule.get("molecule_properties") or {}
            cache[molecule["molecule_chembl_id"]] = {"molecule_chembl_id": molecule["molecule_chembl_id"],
                                                     "canonical_smiles": structures.get("canonical_smiles") or "",
                                                     "full_mwt": properties.get("full_mwt") or ""}
        # An id the endpoint does not return (withdrawn, or no structure) is recorded empty, so the next run does
        # not ask for it again and the count of structureless compounds stays honest.
        for molecule_id in chunk:
            cache.setdefault(molecule_id, {"molecule_chembl_id": molecule_id, "canonical_smiles": "",
                                           "full_mwt": ""})
        if number % 50 == 0:
            _write_smiles_cache(cache, path)
            print(f"  {min(start + batch, len(missing))}/{len(missing)} fetched")
        time.sleep(delay_s)
    _write_smiles_cache(cache, path)
    with_structure = sum(1 for r in cache.values() if r.get("canonical_smiles"))
    print(f"{len(cache)} compounds cached in {path.name}, {with_structure} with a SMILES")
    return cache


def smiles_table(path: Path = SMILES_CACHE) -> pd.DataFrame:
    """The SMILES cache as a frame, with `full_mwt` numeric."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame["full_mwt"] = pd.to_numeric(frame["full_mwt"], errors="coerce")
    return frame


def build_fingerprints(cache_path: Path = SMILES_CACHE, out: Path = FINGERPRINTS) -> tuple[list[str], np.ndarray]:
    """ECFP4 for every cached compound that has a parseable SMILES, saved as a compressed npz.

    Not committed: 115k x 2048 bits is ~30 MB and it is a pure function of the committed SMILES cache, which takes
    under two minutes to rebuild."""
    frame = smiles_table(cache_path)
    frame = frame[frame["canonical_smiles"] != ""]
    ids, rows, failed = [], [], 0
    for molecule_id, smiles in zip(frame["molecule_chembl_id"], frame["canonical_smiles"]):
        bits = ecfp4(smiles)
        if bits is None:
            failed += 1
            continue
        ids.append(molecule_id)
        rows.append(bits)
    matrix = np.packbits(np.array(rows, dtype=np.uint8), axis=1) if rows else np.zeros((0, N_BITS // 8), np.uint8)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, ids=np.array(ids), packed=matrix, n_bits=N_BITS)
    print(f"{len(ids)} fingerprints in {out.name} ({failed} SMILES RDKit could not parse)")
    return ids, matrix


def fingerprints(path: Path = FINGERPRINTS) -> tuple[list[str], np.ndarray]:
    """The cached fingerprint matrix, unpacked to one uint8 0/1 row per compound."""
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing - run `python -m screening.features` first")
    saved = np.load(path, allow_pickle=False)
    bits = np.unpackbits(saved["packed"], axis=1)[:, :int(saved["n_bits"])]
    return [str(i) for i in saved["ids"]], bits


# --- species -----------------------------------------------------------------------------------------------

def fetch_targets(target_ids: list[str], batch: int = BATCH, delay_s: float = DELAY_S) -> pd.DataFrame:
    """target_chembl_id -> target_type, organism, tax_id, pref_name."""
    rows, unique = [], list(dict.fromkeys(i for i in target_ids if i))
    for start in range(0, len(unique), batch):
        chunk = unique[start:start + batch]
        payload = _get("target.json", {"target_chembl_id__in": ",".join(chunk), "limit": batch})
        for target in payload.get("targets", []):
            rows.append({"target_chembl_id": target.get("target_chembl_id"),
                         "target_type": target.get("target_type") or "",
                         "organism": target.get("organism") or "",
                         "tax_id": target.get("tax_id") or "",
                         "target_pref_name": target.get("pref_name") or ""})
        time.sleep(delay_s)
    print(f"{len(rows)}/{len(unique)} targets resolved")
    return pd.DataFrame(rows)


def fetch_organism_table(delay_s: float = DELAY_S) -> pd.DataFrame:
    """ChEMBL's whole `organism` resource: tax_id -> l1 / l2 / l3 (for bacteria, l2 is the Gram call).

    All 4,280 rows in 5 requests, so there is no reason to fetch it selectively."""
    rows, offset = [], 0
    while True:
        payload = _get("organism.json", {"limit": 1000, "offset": offset})
        found = payload.get("organisms", [])
        rows += [{"tax_id": str(o.get("tax_id") or ""), "chembl_l1": o.get("l1") or "",
                  "chembl_l2": o.get("l2") or "", "chembl_l3": o.get("l3") or ""} for o in found]
        offset += len(found)
        if not found or offset >= int(payload.get("page_meta", {}).get("total_count", 0)):
            break
        time.sleep(delay_s)
    print(f"{len(rows)} rows in ChEMBL's organism classification")
    return pd.DataFrame(rows)


def species_genotype_features(species: str) -> dict:
    """The genotype hook. Empty today; see the TODO(final) in this module's docstring.

    Kept as a function rather than a column so that adding it later does not change this file's shape: a caller
    merges whatever it returns into the species row, and an empty dict is the honest answer right now."""
    return {}


def build_species_features(data: Path = DATA, out: Path = SPECIES_CSV) -> pd.DataFrame:
    """One row per species in the matrix: name, genus, tax_ids, ChEMBL's l1/l2/l3, and how much data it has."""
    frame = load_matrix(data)
    targets = fetch_targets(sorted(frame["target_chembl_id"].unique()))
    organisms = fetch_organism_table()
    targets["species"] = [species_key(o) for o in targets["organism"]]

    # A species can own several ChEMBL targets (strains, and sometimes an ORGANISM plus a protein target), so the
    # species row keeps every target and tax id behind it - provenance, and a check for someone who doubts a merge.
    grouped = targets[targets["species"] != ""].groupby("species")
    taxonomy = organisms.drop_duplicates("tax_id").set_index("tax_id")
    rows = []
    for species, group in grouped:
        tax_ids = [t for t in dict.fromkeys(group["tax_id"].astype(str)) if t and t != "nan"]
        classified = [taxonomy.loc[t] for t in tax_ids if t in taxonomy.index]
        counts = frame[frame["species"] == species]
        row = {"species": species, "genus": species.split()[0],
               "n_rows": int(len(counts)), "n_compounds": int(counts["molecule_chembl_id"].nunique()),
               "n_censored": int(counts["censored"].sum()),
               "target_chembl_ids": "|".join(sorted(group["target_chembl_id"])),
               "target_types": "|".join(sorted(set(group["target_type"]))),
               "tax_ids": "|".join(tax_ids),
               "chembl_l1": classified[0]["chembl_l1"] if classified else "",
               "chembl_l2": classified[0]["chembl_l2"] if classified else "",
               "chembl_l3": classified[0]["chembl_l3"] if classified else ""}
        rows.append({**row, **species_genotype_features(species)})
    table = pd.DataFrame(rows).sort_values("n_rows", ascending=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"{len(table)} species in {out.name}; {int((table['chembl_l2'] != '').sum())} carry a ChEMBL l2 "
          "(Gram) call")
    return table


def species_features(path: Path = SPECIES_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing - run `python -m screening.features --species` first")
    return pd.read_csv(path, dtype=str, keep_default_na=False).assign(
        n_rows=lambda f: pd.to_numeric(f["n_rows"]), n_compounds=lambda f: pd.to_numeric(f["n_compounds"]))


def one_hot(table: pd.DataFrame, columns=("chembl_l1", "chembl_l2", "genus")) -> pd.DataFrame:
    """Species features as a numeric frame indexed by species: one-hot over the categorical ranks.

    Not used by the baselines (neither of them looks at a species feature - that is the point of the marginal
    baseline), but it is what a model trained on cold_species needs, so it lives here next to the data."""
    return pd.get_dummies(table.set_index("species")[list(columns)], dtype=int)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--smiles", action="store_true", help="only fetch/cache SMILES and build fingerprints")
    parser.add_argument("--species", action="store_true", help="only build the species feature table")
    args = parser.parse_args()
    both = not (args.smiles or args.species)
    if args.smiles or both:
        fetch_smiles(sorted(load_matrix(args.data)["molecule_chembl_id"].unique()))
        build_fingerprints()
    if args.species or both:
        build_species_features(args.data)


if __name__ == "__main__":
    main()
