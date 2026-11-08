# kg/biology/: the biology knowledge graph

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

A small subgraph around our questions: compounds, their targets, target classes, and known activities (IC50s), plus
similar compounds, whose potencies tell the agent what concentration range to test.

- **Sources:** ChEMBL (activities, targets; API or a dump), UniProt (targets), OptimusKG or PrimeKG (wider biology).
- **Writes:** `graph/nodes.csv`, `graph/edges.csv` in the format in [../README.md](../README.md).
- **Hold-out:** the activities that benchmark questions ask about must **not** be in the graph. Coordinate with
  `benchmark/`, which keeps the list of held-out (compound, target) pairs.
- **Run:** `python -m kg.biology.build` _(to write)_
- **Hold-out rule: leave out every ChEMBL document from 2024 on** (benchmark questions come from those papers);
  `build_seed --before-year` (default 2024) enforces it.

## Seed graph builder

<!-- TODO(final): seed graph for testing; replace with the kg/biology owner's graph. -->
`build_seed.py` builds a seed graph from a **local ChEMBL 37 SQLite dump** (download and placement in
`chembl_db.py`; it lives in the git-ignored `data/raw/chembl/` at the repo root, or set `CHEMBL_SQLITE`):

```bash
python -m kg.biology.build_seed --targets CHEMBL1936 CHEMBL4722      # or --targets-file targets.txt
python -m kg.biology.build_seed --targets ... --compounds new.csv    # + structure-only compounds
```

For each target: its IC50s from documents published before `--before-year` (default 2024; at most the 2,000 most
recent, `CAP_PER_TARGET` in `kg/constants.py`), the compounds (with SMILES), assays and papers (`Document`, with
year, PMID, DOI) behind them, and ChEMBL's protein-class chain (`chembl_class:<id>`). It refuses (`LeakageError`)
to write anything from the cutoff year on. `--compounds` adds molecules with their structure only, so a query can
find a compound the graph has no activity for. Written column-wise in pandas; `WWTN_GPU=1` runs it on the GPU
(`kg/README.md`).

### What is in `graph/` now (for curators)

Built from ChEMBL 37 (documents before 2024) around the 19 kinases in [`seed/targets.txt`](seed/targets.txt), the
targets of the benchmark's candidate papers; [`seed/compounds.csv`](seed/compounds.csv) are those papers' compounds,
added with structure only. 15,359 nodes (12,822 compounds, 1,520 assays, 915 papers, 19 targets, 35 classes) and
19,179 edges (17,719 IC50s). Rebuild after editing either file:

```bash
python -m kg.biology.build_seed --targets-file kg/biology/seed/targets.txt --compounds kg/biology/seed/compounds.csv
```

| ChEMBL target | UniProt | Name | Class | IC50s | Papers | Years |
|---|---|---|---|---|---|---|
| CHEMBL5903 | Q04771 | Activin receptor type-1 | TKL protein kinase STKR1 | 1496 | 46 | 2013–2023 |
| CHEMBL4722 | O14965 | Aurora kinase A | Other protein kinase AUR family | 1997 | 187 | 2012–2023 |
| CHEMBL2793 | P48729 | Casein kinase I isoform alpha | CK1 protein kinase CK1 family | 101 | 33 | 2007–2023 |
| CHEMBL3142 | P78527 | DNA-dependent protein kinase catalytic subunit | Atypical protein kinase PIKK family | 1883 | 80 | 2001–2023 |
| CHEMBL2292 | Q13627 | Dual specificity tyrosine-phosphorylation-regulated kinase 1A | CMGC protein kinase Dyrk1 subfamily | 1812 | 132 | 2003–2023 |
| CHEMBL3357 | P51617 | Interleukin-1 receptor-associated kinase 1 | TKL protein kinase IRAK family | 342 | 39 | 2006–2023 |
| CHEMBL3836 | P53667 | LIM domain kinase 1 | TKL protein kinase LIMK subfamily | 417 | 36 | 2009–2023 |
| CHEMBL4179 | P45984 | Mitogen-activated protein kinase 9 | CMGC protein kinase JNK subfamily | 851 | 118 | 1998–2023 |
| CHEMBL5776 | O43318 | Mitogen-activated protein kinase kinase kinase 7 | TKL protein kinase TAK1 subfamily | 264 | 31 | 2009–2023 |
| CHEMBL5784 | O60285 | NUAK family SNF1-like kinase 1 | CAMK protein kinase NuaK subfamily | 84 | 33 | 2008–2023 |
| CHEMBL5907 | Q9NRM7 | Serine/threonine-protein kinase LATS2 | AGC protein kinase NDR family | 52 | 9 | 2017–2023 |
| CHEMBL6082 | P57059 | Serine/threonine-protein kinase SIK1 | CAMK protein kinase QIK subfamily | 64 | 20 | 2009–2023 |
| CHEMBL6149 | Q9Y2K2 | Serine/threonine-protein kinase SIK3 | CAMK protein kinase QIK subfamily | 71 | 13 | 2017–2023 |
| CHEMBL1075163 | Q8TF76 | Serine/threonine-protein kinase haspin | Other protein kinase Haspin family | 178 | 25 | 2010–2023 |
| CHEMBL2842 | P42345 | Serine/threonine-protein kinase mTOR | Atypical protein kinase FRAP subfamily | 2000 | 134 | 2015–2023 |
| CHEMBL5404 | Q86UE8 | Serine/threonine-protein kinase tousled-like 2 | Other protein kinase TLK family | 7 | 5 | 2017–2022 |
| CHEMBL5251 | Q06187 | Tyrosine-protein kinase BTK | Tyrosine protein kinase Tec family | 1936 | 63 | 2021–2023 |
| CHEMBL5331 | Q12866 | Tyrosine-protein kinase Mer | Tyrosine protein kinase Axl family | 1990 | 57 | 2017–2023 |
| CHEMBL4895 | P30530 | Tyrosine-protein kinase receptor UFO | Tyrosine protein kinase Axl family | 1993 | 84 | 2017–2023 |

Worth a curator's eye:
- **The cap keeps only the newest 2,000 IC50s per target**, so heavily studied kinases lose their older literature
  (BTK only goes back to 2021, mTOR to 2015). Raise `CAP_PER_TARGET` in `kg/constants.py` if that history matters.
- **Thin targets:** TLK2 has 7 IC50s, LATS2 52, SIK1 64, SIK3 71: weak potency priors.
- **Filters:** exact (`=`) IC50s in nM, no ChEMBL validity flag (or "Manually validated"), wild-type assays only.
  Ki/Kd, % inhibition, censored (`>`) values and mutant assays are not in the graph.
- **Only kinases, only ChEMBL:** no pathways, diseases or other targets yet; no UniProt gene names.

## The bacterial MIC graph (`build_bacteria.py`)

For the antimicrobial question — *which compounds inhibit pathogens but spare gut commensals*. A **sibling** to
`build_seed.py`, not a flag on it: `chembl_db.target_info()` returns `None` unless the target is a human
`SINGLE PROTEIN`, and every bacterium in ChEMBL is `target_type = ORGANISM` with no components and no
protein-class chain (*S. aureus* is `CHEMBL352`).

```bash
python -m kg.biology.build_bacteria                                  # all of seed/organisms.csv
python -m kg.biology.build_bacteria --organisms CHEMBL614411 CHEMBL352
```

Reads [`seed/organisms.csv`](seed/organisms.csv) (organism, name, role, oxygen_tolerance, gram) and writes
`graph_bacteria/{nodes,edges}.csv`. Goes over the **REST API** (`chembl_api.py`), so it needs no local dump.

**Commensal-first.** The commensal arm is pulled whole (~1,500 usable records across six species); the pathogen
arm only for the compounds that arm found. *S. aureus* alone has 160k MIC records, and pulling pathogens first
gives a graph that is almost entirely rows sharing no compound with any commensal. Measured overlap: 495 of the
632 compounds with a commensal MIC also have one on *S. aureus* — an 82% pairing rate, because people measure a
commensal precisely when they care about selectivity.

Three filters differ from the kinase build, on purpose:

| | `build_seed.py` (IC50) | `build_bacteria.py` (MIC) |
| --- | --- | --- |
| relation | `=` only | `=` **and `>`** — a `>128 ug/mL` on a commensal is the finding, not a gap; ~25% of records on every organism are censored |
| units | `nM` only | `ug.mL-1` **and** `nM`, unconverted (converting needs a molecular weight); the edge carries value *and* unit |
| dropped | — | `ug cm**-2` (surface-coating assays — 12% of *E. coli*'s records) and `p.p.m.` |

**No year cutoff is applied.** The hold-out is a separate filter over the built graph. With 495 paired compounds
a **document-level** split is affordable (~100 test compounds); the 2024 cutoff would leave about forty.

`role`, `oxygen_tolerance` and `gram` are **hand-curated** — ChEMBL holds none of them. They are what
`wwtn.schema.PanelMember` needs and what `execution/feasibility.py` checks against, so they live on the Organism
node. <!-- TODO(final): source these from BacDive or KG-Microbe instead of by hand. -->

Known traps in this graph:
- **Species-level data hides resistance.** Clindamycin reads 0.125 ug/mL on *S. aureus* and **>128** on
  *B. fragilis*, which says it spares the commensal — the opposite of the truth, since clindamycin is the
  textbook cause of *C. difficile* colitis. That record is a resistant isolate, and ChEMBL cannot distinguish
  "intrinsically spared" from "this strain is resistant".
  <!-- TODO(final): take the minimum MIC per species, or parse strain from the assay description. -->
- **There is no class chain**, so no `TargetClass` bridge to `kg/protocols/` yet. The taxonomic equivalent is
  ChEMBL's `organism_class` table, or traits (Gram, oxygen tolerance) which map onto protocol choice directly.
