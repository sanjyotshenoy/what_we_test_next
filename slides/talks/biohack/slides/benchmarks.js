// The two benchmarks, as bar-chart templates to fill in (Deck.groupedBars): the metrics along the bottom, one bar
// per model, every bar empty and labelled "—" until the runs are in. The slides double as the plan for running
// them (setup in the footnote, details in the speaker notes). Load with Deck.section(3) before it; the slides go
// ahead of 'blank-6' (Results).
//   bench-propose         benchmark 1, the headline: overall score bare → + literature → + both KGs, a setting a click
//   bench-propose-fields  benchmark 1 field by field, in the + both KGs setting (one step)
//   bench-code            benchmark 2: does the OT-2 protocol run (one step)
//
// MODELS is the shortlist on Nebius Token Factory; keep it in step with EVAL_MODELS in wwtn/llm.py. Every value is
// a percentage of questions: fill one in as RESULTS[chart][model id][group key], e.g.
//   RESULTS.propose['moonshotai/Kimi-K3'] = { bare: 40, lit: 55, kg: 80 };
{
const MODELS = [
  { id: 'deepseek-ai/DeepSeek-V4-Pro-0813', name: 'DeepSeek V4 Pro' },
  { id: 'moonshotai/Kimi-K3', name: 'Kimi K3' },
  { id: 'Qwen/Qwen3.8-27B', name: 'Qwen3.8 27B' },
  { id: 'zai-org/GLM-5.3', name: 'GLM-5.3' },
];

const RESULTS = { propose: {}, fields: {}, code: {} };

const CHARTS = [
  {
    name: 'bench-propose',
    key: 'propose',
    heading: 'Benchmark 1: is the proposed experiment right?',
    groups: [
      { key: 'bare', label: ['Bare', 'LLM'], step: 1 },
      { key: 'lit', label: ['+ Literature', 'search'], step: 2 },
      { key: 'kg', label: ['+ Both', 'KGs'], step: 3, highlight: true },
    ],
    footnote: 'Overall score on held-out questions (IC50 removed from the KB), graded field by field against the '
      + 'held-out ChEMBL assay · same prompt for every model',
    notes: 'How to run it: benchmark/ writes questions.jsonl and ground_truth.jsonl; agent/ runs each model three '
      + 'ways (bare, + literature search, + both KGs) and writes ExperimentProposal lines; python -m benchmark.grade '
      + 'scores them. One click per setting; the last one, + both KGs, is the headline: the lift the graphs give.',
  },
  {
    name: 'bench-propose-fields',
    key: 'fields',
    heading: 'Benchmark 1, field by field',
    groups: [
      { key: 'abstain', label: ['Abstains'] },
      { key: 'assay', label: ['Assay,', 'readout'] },
      { key: 'range', label: ['Range hits', 'IC50'], highlight: true },
      { key: 'series', label: ['Series,', 'controls'] },
    ],
    footnote: 'With both KGs · "abstains": says the KB can’t answer instead of quoting a memorized IC50 · "range '
      + 'hits IC50": the true IC50 falls inside the proposed series',
    notes: 'Each bar is the share of questions where that field matches the ground truth. "Range hits IC50" is '
      + 'where grounding in similar compounds should beat a guess; penalize very wide ranges in the grader, or a '
      + 'wide screen always wins. Four groups is what fits; check cited KG node IDs too, but report that as a '
      + 'number in the text (it is near 100% by construction when citations come from retrieval).',
  },
  {
    name: 'bench-code',
    key: 'code',
    heading: 'Benchmark 2: does the OT-2 protocol run?',
    groups: [
      { key: 'sim1', label: ['Runs,', 'first try'] },
      { key: 'sim3', label: ['Runs,', '≤ 3 fixes'] },
      { key: 'wells', label: ['Wells match', 'reference'], highlight: true },
      { key: 'e2e', label: ['End to', 'end'] },
    ],
    footnote: 'Every model writes OT-2 code for the same ground-truth experiments · run in opentrons_simulate · '
      + 'compared with the hand-written reference protocol',
    notes: 'How to run it: give every model the ground-truth experiment (not its own proposal), ask for an OT-2 '
      + 'protocol, run opentrons_simulate; on an error, feed it back, up to 3 times. "Wells match": the final '
      + 'concentration in each well agrees with the reference protocol. "End to end": the same, starting from the '
      + 'model\'s own benchmark-1 proposals. Report cost per protocol alongside. The simulator catches API and deck '
      + 'errors, not wrong biology.',
  },
];

CHARTS.forEach((c) => Deck.slide(c.name, {
  steps: Math.max(...c.groups.map((g) => g.step || 1)),
  before: 'blank-6',
  notes: c.notes,
  mount(frame, { esc }) {
    frame.innerHTML = `<h2 class="deck-heading reveal-in in">${esc(c.heading)}</h2>`;
    // plain numbers on a 0..100 axis; a missing result is an empty bar labelled "—"
    const plot = Deck.groupedBars(frame, {
      max: 100,
      format: (v) => (v == null ? '—' : `${Math.round(v)}%`),
      series: MODELS.map((m) => ({ key: m.id, label: m.name })),
      groups: c.groups.map((g) => ({ ...g,
        values: Object.fromEntries(MODELS.map((m) => [m.id, (RESULTS[c.key][m.id] || {})[g.key] ?? null])) })),
      footnote: [c.footnote],
    });
    return { enter: (step, animate) => plot.show(step, animate) };
  },
}));
}
