// The two benchmarks, as templates to fill in: one slide each, the models down the side and the metrics across,
// every cell "—" until the runs are in. The slides double as the plan for running them (setup in the lead line,
// details in the speaker notes). Load with Deck.section(3) before it; both slides go ahead of 'blank-6' (Results).
// Steps: 1 heading, setup and the empty table · 2 the caption (what is held fixed, where the numbers come from).
//
// MODELS is the shortlist on Nebius Token Factory; keep it in step with EVAL_MODELS in wwtn/llm.py. To fill a
// cell, put its value in RESULTS under the model's ID and the column's key.
{
const MODELS = [
  { id: 'deepseek-ai/DeepSeek-V4-Pro-0813', name: 'DeepSeek V4 Pro' },
  { id: 'moonshotai/Kimi-K3', name: 'Kimi K3' },
  { id: 'Qwen/Qwen3.8-27B', name: 'Qwen3.8 27B' },
  { id: 'zai-org/GLM-5.3', name: 'GLM-5.3' },
];

// e.g. RESULTS.propose['moonshotai/Kimi-K3'] = { abstain: '9/10', ... }
const RESULTS = { propose: {}, code: {} };

const BENCHMARKS = [
  {
    name: 'bench-propose',
    key: 'propose',
    heading: 'Benchmark 1: is the proposed experiment right?',
    lead: 'For each held-out question, every model proposes an experiment: bare, with literature search, and with '
      + 'both KGs.',
    columns: [
      ['abstain', 'Abstains'],
      ['assay', 'Assay, readout'],
      ['range', 'Range hits IC50'],
      ['series', 'Series, controls'],
      ['cited', 'Valid citations'],
      ['score', 'Score: bare / +lit / +KGs'],
    ],
    caption: 'Graded field by field against the held-out ChEMBL assay · same prompt for every model',
    notes: 'How to run it: benchmark/ writes questions.jsonl and ground_truth.jsonl; agent/ runs each model in three '
      + 'settings (bare, + literature, + both KGs) and writes ExperimentProposal lines; python -m benchmark.grade '
      + 'scores them. "Says the KB can\'t answer" checks it did not quote a memorized IC50. "Range brackets the IC50" '
      + 'is where grounding in similar compounds should beat a guess.',
  },
  {
    name: 'bench-code',
    key: 'code',
    heading: 'Benchmark 2: does the OT-2 protocol run?',
    lead: 'Each model writes OT-2 code for the same ground-truth experiments, then end to end from its own '
      + 'proposals.',
    columns: [
      ['sim1', 'Runs, first try'],
      ['sim3', 'Runs, ≤ 3 fixes'],
      ['wells', 'Wells match'],
      ['valid', 'Volumes, tips OK'],
      ['e2e', 'End to end'],
      ['cost', 'Cost per protocol'],
    ],
    caption: 'Run in opentrons_simulate · compared with the hand-written reference protocol',
    notes: 'How to run it: give every model the ground-truth experiment (not its own proposal), ask for an OT-2 '
      + 'protocol, run opentrons_simulate; on an error, feed the error back, up to 3 times. "Wells match" compares the '
      + 'final concentration in each well with the reference protocol. Then repeat from each model\'s own '
      + 'benchmark-1 proposals for the end-to-end column. The simulator catches API and deck errors, not wrong biology.',
  },
];

BENCHMARKS.forEach((b) => Deck.slide(b.name, {
  steps: 2,
  before: 'blank-6',
  notes: b.notes,
  mount(frame, { css, esc }) {
    css(`
      .bm-table { position: absolute; left: 4.2%; right: 4.2%; top: 30%; border-collapse: collapse;
        font-size: var(--t-small); }
      .bm-table th { font-size: var(--t-caption); font-weight: 600; color: var(--muted); text-align: center;
        vertical-align: bottom; padding: 0 .5em .6em; line-height: 1.2;
        border-bottom: 1.5px solid color-mix(in srgb, var(--muted) 45%, transparent); }
      .bm-table th:first-child { text-align: left; padding-left: 0; }
      .bm-table td { text-align: center; padding: .4em .5em;
        border-bottom: 1px solid color-mix(in srgb, var(--muted) 18%, transparent); }
      .bm-table td:first-child { text-align: left; padding-left: 0; white-space: nowrap; }
      .bm-table td.bm-empty { color: var(--muted); }
      .bm-table th.bm-key, .bm-table td.bm-key { color: var(--accent); font-weight: 700; }
      .bm-model { font-weight: 700; }
      .bm-id { display: block; font-size: var(--t-micro); }
    `);
    const last = b.columns.length - 1;  // the column the slide is about: accent
    const cell = (m, [key], i) => {
      const v = (RESULTS[b.key][m.id] || {})[key];
      const cls = [v == null ? 'bm-empty' : '', i === last ? 'bm-key' : ''].filter(Boolean).join(' ');
      return `<td class="${cls}">${v == null ? '—' : esc(String(v))}</td>`;
    };
    frame.innerHTML = `
      <h2 class="deck-heading reveal-in" data-from="1">${esc(b.heading)}</h2>
      <p class="deck-lead reveal-in" data-from="1" style="--i:1">${esc(b.lead)}</p>
      <table class="bm-table reveal-in" data-from="1" style="--i:2">
        <thead><tr><th>Model</th>${b.columns.map(([, label], i) =>
          `<th class="${i === last ? 'bm-key' : ''}">${esc(label)}</th>`).join('')}</tr></thead>
        <tbody>${MODELS.map((m) => `<tr><td><span class="bm-model">${esc(m.name)}</span>
          <span class="bm-id deck-detail">${esc(m.id)}</span></td>${b.columns.map((c, i) => cell(m, c, i)).join('')}</tr>`).join('')}
        </tbody>
      </table>
      <p class="deck-caption reveal-in" data-from="2">${esc(b.caption)}</p>`;
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
}));
}
