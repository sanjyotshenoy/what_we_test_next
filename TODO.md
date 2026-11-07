# Before we present

Everything mock, placeholder or unconfirmed is tagged `TODO(final)` where it lives. The live list is always:

```bash
grep -rn "TODO(final)" --exclude-dir=.git .
```

When you leave something fake or unfinished behind, add a `TODO(final): ...` comment at that spot; when you fix
it, delete the comment. The checklist below is a snapshot for orientation; the grep is the source of truth.

**On screen (embarrassing if forgotten)**
- [ ] Demo plays a mock trace with a "Mock trace" badge: replace `slides/talks/biohack/demo/runs/kit_imatinib.js`
  with a real run, `mock: false`, real held-out ChEMBL assay ID (also `demo/index.html`, `slides/demo.js` notes)
- [ ] Benchmark charts are empty ("—"): fill `RESULTS` in `slides/talks/biohack/slides/benchmarks.js`
- [ ] Slides that still say "Placeholder: ...": `slides/talks/biohack/slides/blank.js`
- [ ] Outline is the dummy one: confirm `slides/talks/biohack/slides/outline.js`
- [ ] Title slide photos for Emmy Nguyen, Jimmy Hsu, Xiaochen Zhai: `slides/talks/biohack/slides/title.js`

**Behind the scenes**
- [ ] Confirm the four benchmark models are live on our key: `wwtn/llm.py` and `benchmarks.js`
- [ ] Pick the range-accuracy metric before writing the grader: `benchmark/README.md`
- [ ] Owners in each folder README: `agent/`, `execution/`, `benchmark/`, `kg/biology/`, `kg/protocols/`
