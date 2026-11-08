# Process-story prototype

Review-only alternative to slides 8–10. Open index.html in a browser; arrows advance the three steps per slide, T changes theme. The main biohack deck does not load these files.

1. Real source records for CHEMBL420452, with two measured species and two missing pairs in the committed bacterial snapshot. Click a measured species to inspect its assay.
2. Reusable template stages and provenance for two-fold spacing, separated from the hand-written design inputs.
3. Actual existing compiler plate output, progressively revealing the series, replicate/species rows and controls.

The transition between the source records and the hand-written plate example is illustrative; this is not a verified end-to-end proposal for this compound. TODO(final): replace that handoff with a reviewed trace before claiming end-to-end operation. Missing graph records are not evidence of scientific novelty. The reference-antibiotic control is absent in the example layout and remains flagged.

Sources: kg/biology/graph_bacteria CSVs, kg/protocols/templates/bacterial_mic_broth.json, execution/examples/mic_selectivity.jsonl, and biohack/evidence/data.js. Regenerate selected source data from the repository root with `python3 -m slides.talks.process-prototype.prep`.
