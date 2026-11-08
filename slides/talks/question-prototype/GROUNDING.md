# Slide grounding — 2026-11-08

The researcher supplies compound X, specified bacterial strains and a question. Compound discovery and strain selection are upstream. The query guides assay selection; the LLM may interpret it, and an optional assay preference can narrow retrieval.

Assume an up-to-date KB. The missing-link illustration represents a genuinely unanswered question. Return known evidence with citations, leaving the decision to run another experiment to the researcher. Hiding known evidence is an evaluation simulation, not a claim about incomplete literature in the demo.

Ground protocol design in existing templates, examples and lab constraints. Whether LLM step assembly improves on template selection and parameter filling is an open evaluation question. Evaluate experiment suitability, procedural soundness and numerical soundness separately.

An incompatible proposal may be shown with limitations or stopped, but must not enter compilation or hardware execution. This is the agreed requirement, not a claim that the current executor implements every gate.

## Prototype

1. `missing-link`: keep the accepted two-compound/three-strain bipartite graph; reveal the question, X/Y labels, zoom/dim and missing connection.
2. `grounded-design`: supplied inputs → assay selection → grounded adaptation → compatibility check, with separate compatible and incompatible outcomes.

These are conceptual illustrations, not recorded queries. `story.js` contains the content and animations. The main deck's opening story and motivation now use the same supplied-input scope and distinguish known evidence from unanswered questions.
