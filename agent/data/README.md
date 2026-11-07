# agent/data/sample_kg: a hand-written stand-in for the two graphs

<!-- TODO(final): delete this folder once kg/biology/graph/ and kg/protocols/graph/ exist; agent.tools falls back
     to it only while they are missing. Every number here (IC50s, similarities) is approximate, not from ChEMBL. -->

The same node/edge CSV format as [kg/README.md](../../kg/README.md), just enough to run the agent end to end
before `kg/` writes its graphs: a few kinase inhibitors, three tyrosine kinases, one biochemical dose-response
protocol template. The pair **imatinib × KIT is deliberately absent** (the held-out fact the demo question asks
about); imatinib's activities on ABL1 and PDGFRB are present, as are three analogs with KIT activity.
