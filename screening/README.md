# screening/: virtual pre-screening, upstream of the MIC assay

Owner: open (built by a coding agent, 2026-11-07/08 — nothing here has been reviewed by a person yet).

> **State of this folder: plumbing and plan, no data.** Nothing under `data/`, `splits/` or `results/` is
> committed, and **there are no result numbers anywhere in this README** — by design. The matrix is meant to be
> built on the machine that has the ChEMBL dump (a DGX Spark), not here. The REST fetch *was* run once during
> development and then discarded, which is where the one empirical observation below comes from (the fungi in
> the mid-sized species band); `splits.py`, `features.py` and `baseline.py` have only ever run against the
> small fixtures in `tests/`. `features.py` has no tests at all yet. Treat every runtime estimate as an
> estimate.

**The question this stage answers:** given a candidate antimicrobial compound, which bacterial species does it
inhibit? Ideally it hits the pathogens and spares the gut commensals. That ranking decides which candidates are
worth a real MIC plate, so this sits *upstream* of everything else in the repo: `screening/` picks the compound,
[`agent/`](../agent/) proposes the experiment, [`execution/`](../execution/) turns it into an OT-2 protocol, and
Emmy's broth microdilution in [`Opentrons/`](../Opentrons/) runs it. The downstream panel is already agreed
(DISCUSSIONS.md): *C. difficile* (CHEMBL614965), *E. faecalis* (CHEMBL362), *B. fragilis* (CHEMBL614411) and
*B. longum* (CHEMBL613911), the last being the commensal we want spared.

This folder is **data plumbing only**. There is no model in it yet — just the matrix, the splits everybody must
share, the features, and two baselines that say how much there is to beat. See "Not done yet".

## What is here

| File | What it does | Writes |
| --- | --- | --- |
| `fetch_mic.py` | every `standard_type=MIC` activity, from a local ChEMBL 37 dump or (fallback) the REST API | `data/mic_matrix.csv` |
| `splits.py` | cuts the shared train/val/test splits, and the loader everything downstream must use | `splits/*.json` |
| `features.py` | ECFP4 per compound; species features from ChEMBL + NCBI taxonomy | `data/smiles.csv.gz`, `data/species_features.csv`, `data/ecfp4.npz` |
| `baseline.py` | chemical-similarity kNN vs. a species-marginal baseline | `results/baseline.json` |
| `tests/` | offline tests on hand-written fixtures (no network) | — |

## Step 0: get the data (do this first, on the machine with the disk)

**Use the ChEMBL SQLite dump, not the REST API.** One query answers the whole table, it brings canonical SMILES
and molecular weights along (which also replaces the ~116k molecule lookups `features.py` would otherwise make),
it takes seconds instead of ~45 minutes, and it is reproducible — the same dump gives the same table forever.

```bash
mkdir -p data/raw/chembl && cd data/raw/chembl          # already git-ignored at the repo root
curl -O https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/chembl_37_sqlite.tar.gz
tar xzf chembl_37_sqlite.tar.gz
# -> data/raw/chembl/chembl_37/chembl_37_sqlite/chembl_37.db
```

**5.8 GB down, ~30 GB unpacked.** That is the same path and the same `CHEMBL_SQLITE` environment variable
[`kg/biology/chembl_db.py`](../kg/biology/chembl_db.py) already uses, so one download serves both.

**Pin to ChEMBL 37, not "latest."** `kg/biology/chembl_db.py` is checked against 37 and the seed biology graph
was built from it. A different release shifts the counts, and a split cut from a different matrix is not
comparable to anything else in the repo — which is the entire point of the splits.

The REST path exists for a machine where 30 GB is not worth it (`--source rest`). It needs no download but
takes ~45 minutes over 6 sharded streams, and it does not return SMILES, so `features.py` then has to make the
116k lookups itself.

## How to run it

From the repo root, with `requirements.txt` installed:

```bash
python -m screening.fetch_mic                  # uses the dump if present, else REST; writes data/mic_matrix.csv
python -m screening.splits                     # cut the splits ONCE, then share them - see below
python -m screening.features                   # SMILES -> ECFP4, plus the species table
python -m screening.baseline                   # both baselines -> results/baseline.json
python -m pytest -q screening                  # the tests; no network, no real data, seconds
```

### Cut the splits once, then commit them

`splits/cold_compound.json` and `splits/cold_species.json` are **the most important artifact in this folder**,
and they are meant to exist as explicit ID lists that everybody shares. A split regenerated per machine — even
from the same seed — drifts the moment pandas, the matrix or Python's hashing changes, and then two people's
numbers are no longer comparable.

They are **not in the repo today**, because the matrix they would be cut from is not either. So: whoever first
builds the matrix should run `python -m screening.splits`, commit the two JSON files, and tell everyone else.
From then on, read them with `screening.splits.Split.load(...)` and **never re-randomise downstream**.
Regenerating them after that invalidates every number anyone has published, so it is a deliberate act, not a
build step. Each file records the seed, the scoped row count and the matrix's sha256, so a mismatch is caught —
as a warning rather than a crash, because the matrix changes whenever someone re-runs `fetch_mic.py` against a
newer ChEMBL and the older split is still the one the published numbers were measured on.

## What the data is

Verified against the live ChEMBL API on 2026-11-07/08, not estimated:

| | |
| --- | --- |
| MIC activities (`standard_type=MIC`) | **798,852** |
| organism targets (`target_type=ORGANISM`) | 1,281 |
| distinct compounds | 115,942 |
| assays / papers | 89,967 / 8,916 |
| in µg/mL | ~81% (most of the rest are molar) |
| with `standard_relation = '='` | ~74% |
| from 2023 or later | 78,809 (~10%), so a clean time split is viable |

Three properties of those rows decide how the modelling has to work:

- **Units are mixed.** Filter on `standard_units`; do not assume. Molar rows need a molecular weight to convert,
  which the SQLite dump supplies and the REST path does not.
- **A quarter of the rows are censored.** `>` or `<`, not `=`. ">128 µg/mL" means "we stopped looking", not "the
  MIC is 128" — and these are disproportionately the *commensal* rows, which are exactly the ones this stage
  cares about. They must be handled as threshold observations, not dropped and not treated as numbers.
- **The two halves are wildly unbalanced.** 245,556 compound × species pairs on the pathogen side against
  **1,812** for gut commensals — a ~74× asymmetry. A `cold_species` score computed on ChEMBL's commensal rows
  alone is measured on almost nothing, which is why item 3 under "Not done yet" matters so much.

Species-level counts, if you need them for choosing holdouts: *S. aureus* 160,257 · *P. aeruginosa* 57,708 ·
*S. pneumoniae* 24,868 · *Haemophilus* 6,921 · *C. difficile* 2,471 · *Moraxella* 2,667 · *Burkholderia* 1,449 ·
*Stenotrophomonas* 1,415 · *Prevotella* 550 · *Fusobacterium* 400 · *Actinomyces* 265 · *Veillonella* 60 ·
*Rothia* 1.

One thing worth knowing before you pick holdouts, found during the discarded development pull: **run without a
kingdom filter and the mid-sized species band is full of fungi** (*Penicillium chrysogenum*, *Lichtheimia
corymbifera*, *Trichoderma viride*), because ChEMBL's MIC rows include antifungal assays. Holding those out
would measure generalisation across kingdoms, which is not the question. `splits.bacteria(...)` is the filter;
pass it as `only=`.

### Results

**None.** No baseline has been run against the real matrix, so there is no number here to compare against. The
first person to build the matrix produces them, and `results/baseline.json` is where they land.

## Known caveats

Each is also a `TODO(final)` where it lives (`grep -rn "TODO(final)" screening`).

- **ChEMBL is species-level, not strain-level.** Only ~10 of its organism targets are strain-resolved; strain IDs
  live in assay free text. `splits.species_key()` therefore reduces every organism name to a genus + species
  binomial, so "Staphylococcus aureus subsp. aureus" and "... H37Rv" are one species. That is the right call for
  holding a species out, but it does merge genuinely different strains, resistant and susceptible alike.
- **MIC is one number from many protocols.** Broth vs. agar dilution, different media, different inocula, and
  ChEMBL does not normalise them. The matrix keeps `assay_chembl_id` and `document_chembl_id` so a suspicious
  value can be traced, but nothing here corrects for protocol.
- **Unit conversion needs a molecular weight.** 81% of rows are in ug.mL-1 and convert directly; molar rows are
  converted with ChEMBL's `full_mwt` (which the SQLite dump supplies and the REST path does not), and a row with
  neither is dropped and counted into `results/baseline.json` when it runs. None are guessed.
- **The evaluation is capped at 2,000 rows per species** (`--cap`), a runtime cap on an O(eval x train) kNN, with
  the sampling seed recorded. Never exercised at that scale - the cap has only ever been hit by fixtures. *S. aureus* alone has 160,257 MIC rows.
- **Censored rows are a quarter of the matrix, not an edge case.** A novel compound's commensal reading is usually
  ">128 ug/mL". They are flagged (`censored`), excluded from Spearman/MAE (there is no value to correlate) and
  scored as a threshold call in the balanced accuracy. A real model should use a censored likelihood instead.
- **Nobody has reviewed any of this, and nothing has been run on real data.** `splits.py`, `features.py` and
  `baseline.py` have only ever run against `tests/fixtures/`; `features.py` has no tests at all. The first real
  run should be treated as a debugging session, not as a measurement.

## Not done yet

In the order they would help:

1. **Genotype features.** The species features are only what ChEMBL and NCBI already assert: organism name,
   `tax_id`, genus, and ChEMBL's own `l1`/`l2`/`l3` organism classification (`l2` is a curated Gram call). The
   intended next addition is **presence of a homolog of the compound's target in the species' genome, known
   resistance genes (beta-lactamases, efflux pumps), and a cell-envelope call that does not come from ChEMBL's l2
   bucket**. These need a genome source (NCBI assembly, or a curated table) and are deliberately absent rather
   than guessed — a made-up genotype feature would make `cold_species` look solved while predicting nothing.
   `features.species_genotype_features()` is the hook; it returns `{}` today and every caller handles that.
2. **The GNN.** The whole point of the matrix and the splits is to train a compound x species model — a message
   passing network over the molecular graph with a species embedding (and, once (1) exists, species features
   instead of a free embedding). Nothing of it is written. The baselines in `results/baseline.json` are what it
   has to beat, and `cold_species` is where it has to beat them.
3. **Maier et al. 2021 as the external validation set — needs a person.** The 815 commensal MICs in
   [doi:10.1038/s41586-021-03986-2](https://doi.org/10.1038/s41586-021-03986-2) are the only sizeable set of gut
   commensal MICs anywhere, and they are in a **supplementary spreadsheet that cannot be downloaded
   programmatically**: someone has to fetch it from the publisher's page by hand, drop it in
   `screening/data/raw/` (git-ignored), and then it needs its species names normalised to
   `splits.species_key()`'s binomials before it can be joined. It is the right external validation set precisely
   because it is not in ChEMBL — ChEMBL's commensal side is 1,812 compound x species pairs against 245,556
   pathogen ones, so a `cold_species` score on ChEMBL alone is measured on almost nothing.
4. **A censored likelihood** instead of excluding censored rows from the regression metrics.
5. **Protocol normalisation** — at minimum, splitting broth from agar dilution, since the gut commensals in the
   panel are anaerobes that need CLSI M11 agar dilution, not the M07 broth microdilution `execution/` generates.
