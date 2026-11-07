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
(`kg/README.md`). No graph is committed yet: the first one gets built once the target list is settled.
