# kg/biology/: the biology knowledge graph

**Owner:** _(fill in)_ <!-- TODO(final): owner -->

A small subgraph around our questions: compounds, their targets, target classes, and known activities (IC50s), plus
similar compounds, whose potencies tell the agent what concentration range to test.

- **Sources:** ChEMBL (activities, targets; API or a dump), UniProt (targets), OptimusKG or PrimeKG (wider biology).
- **Writes:** `graph/nodes.csv`, `graph/edges.csv` in the format in [../README.md](../README.md).
- **Hold-out:** the activities that benchmark questions ask about must **not** be in the graph. Coordinate with
  `benchmark/`, which keeps the list of held-out (compound, target) pairs.
- **Run:** `python -m kg.biology.build` _(to write)_
