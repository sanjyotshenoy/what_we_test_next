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
