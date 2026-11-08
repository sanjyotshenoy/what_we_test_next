# Knowledge-base story and masking visualization

The construction slides explain the implemented data path, not a demonstrated PDF extraction pipeline. Biology imports ChEMBL records. Protocol templates are agent-curated from PubChem/NCATS sources (with a team reference for MIC); human domain review remains pending. Four retrieval tools exist in `agent/tools.py`, while the pilot uses fixed packets without tool calls.

## Real graph view

Regenerate with `python3 -m slides.tools.prep_kb_story` from the repository root. `kb_story.json` records the source SHA-256 hashes and the full excluded edge records. The exporter asserts that the hashes match the case-1 audit and that the exclusion count matches. It does not modify either source graph.

The overview contains all 15,452 unique nodes from the kinase biology and protocol snapshots. Of 19,478 CSV edges, 19,473 have both endpoints present and can be drawn; five dangling edges are omitted. This is not the separate bacterial MIC snapshot. Coordinates are deterministic and illustrative, not biochemical distance or similarity. Zooming filters the display to the endpoints of the excluded edges, five retained comparison compounds and the applicable protocol class chain; it is not a complete induced neighborhood. The fourth click conceals eight source nodes and 24 affected edges in that display. It does not delete those records from the shared knowledge base.

## Information concealment

Biology: exclude all measurements for the query compound–target pair, every document supporting those measurements, associated assays, and every edge incident to or referencing those sources. Case 1 has two pair measurements, two documents, six assays and 24 excluded edges.

Protocols: the pilot does not mutate the raw protocol graph. It withholds raw protocol text, numeric defaults and quotes from the input packet, substituting seven manually generalized step cards with parameter slots. This is not a proven automatic de-identification or numeric masking process. Retained comparison measurements may still contain numbers; those are intentional evidence.

The model receives only `graph/cases/case-1.input.json`, not the remaining graph or the reviewer visualization. The reviewer toggle is not an access-control mechanism. TODO(final): complete cross-source duplicate/leakage review and expert validation. See `graph/BENCHMARK.md` for the full benchmark design.

## Slides 4–6 source examples (preview revision)

`slides/source_examples.js` replaces the abstract construction diagrams with three click stages each. Slide 4 uses the literal ChEMBL MIC records exported by `talks/process-prototype/prep.py` into its `data.js`: CHEMBL420452, assays CHEMBL876060 / CHEMBL875007, document CHEMBL1133633. The displayed source text is a ChEMBL assay description, not a quotation extracted from a paper PDF. Source references are edge metadata; the diagram is a small selected view.

Slide 5 quotes the observed dilution evidence in `kg/protocols/templates/bacterial_mic_broth.json` (PubChem AID 449774) and shows a method summary. Slide 6 shows the actual `APPLICABLE_TO` relationship to `chembl_target_type:ORGANISM` and the broth-growth requirement from the protocol graph. Query interpretation is illustrative, not an executed routing trace. No claim is made that the earlier paper supplied this protocol or that a connected agent run produced these artifacts.
