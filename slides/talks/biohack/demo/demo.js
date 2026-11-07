// The demo page: plays one trace (runs/*.js, format in README.md) as a timeline of stages, one per "Next step"
// or one every STEP_MS after "Run". A query that matches no trace says so: the page is static until a backend
// serves traces, and then only find() needs to change.
(function () {
  'use strict';

  const STEP_MS = 1100;
  const runs = window.DEMO_RUNS || [];
  const params = new URLSearchParams(location.search);
  if (params.get('theme')) document.documentElement.dataset.theme = params.get('theme');

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const callText = (tool, args) => `${esc(tool)}(${Object.entries(args)
    .map(([k, v]) => `<span class="arg">${esc(k)}=</span>${esc(JSON.stringify(v))}`).join(', ')})`;
  const table = (rows, columns) => `<div class="table-wrap"><table>${columns
    ? `<tr>${columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>` : ''}${rows
    .map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table></div>`;
  const pill = (text, kind) => `<span class="pill ${kind}">${esc(text)}</span>`;

  // the wells: a 1:factor series across columns 1..points of the given rows, darker = more compound
  function plateMap(p) {
    const cols = Array.from({ length: 12 }, (_, i) => i + 1);
    const fill = (r, c) => {
      if (!p.rows.includes(r)) return '';
      if (c <= p.points) return `background: color-mix(in srgb, var(--accent) ${Math.round(100 - 85 * (c - 1) / (p.points - 1))}%, transparent)`;
      if (p.controls[c] === 'DMSO') return 'background: color-mix(in srgb, var(--muted) 30%, transparent)';
      if (p.controls[c]) return 'background: var(--bad)';
      return '';
    };
    const conc = (c) => p.top_uM / p.factor ** (c - 1);
    const fmt = (v) => (v >= 1 ? `${+v.toPrecision(2)} µM` : `${+(v * 1000).toPrecision(2)} nM`);
    return `<div class="plate"><span></span>${cols.map((c) => `<span class="lab">${c}</span>`).join('')}
      ${'ABCDEFGH'.split('').map((r) => `<span class="lab">${r}</span>${cols.map((c) =>
        `<span class="w" style="${fill(r, c)}" title="${r}${c}${p.rows.includes(r) && c <= p.points ? ` · ${fmt(conc(c))}` : ''}"></span>`).join('')}`).join('')}</div>
      <div class="legend"><span><i style="background: var(--accent)"></i>${fmt(p.top_uM)} → ${fmt(conc(p.points))}, 1:${p.factor}</span>
        <span><i style="background: color-mix(in srgb, var(--muted) 30%, transparent)"></i>vehicle</span>
        <span><i style="background: var(--bad)"></i>positive control</span></div>`;
  }

  // one entry per stage: [title, status pill or '', body html]
  function stages(run) {
    const e = run.proposal.experiment;
    const fields = [
      ['Assay', e.assay_type], ['Readout', e.readout], ['System', e.system],
      ['Series', `${e.top_concentration_uM} µM top, 1:${e.dilution_factor}, ${e.n_points} points`],
      ['Replicates', e.replicates], ['Controls', e.controls.join(' · ')],
    ];
    const v = run.validation;
    const passed = v.checks.filter(([, ok]) => ok).length;
    return [
      ['Ask the knowledge base', pill(run.lookup.verdict, 'unknown'), `
        <div class="card"><div class="call">${callText(run.lookup.tool, run.lookup.args)}</div>
          <p>${esc(run.lookup.result)}</p><p class="muted">${esc(run.lookup.note)}</p></div>`],
      ['Query the knowledge graphs', '', run.calls.map((c) => `
        <div class="card"><div class="call">${callText(c.tool, c.args)}</div>
          <p class="muted">${esc(c.summary)}</p>${table(c.rows, c.columns)}</div>`).join('')],
      ['Reason about the gap', '', `<div class="card"><ol class="reasoning">${run.reasoning
        .map((r) => `<li>${esc(r)}</li>`).join('')}</ol></div>`],
      ['Propose the missing experiment', '', `
        <div class="card"><dl class="fields">${fields.map(([k, x]) => `<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`).join('')}</dl>
          <div class="chips">${run.proposal.citations.map((c) => `<span class="chip">${esc(c)}</span>`).join('')}</div></div>`],
      ['Write the procedure and the robot script', pill(run.simulation.ok ? 'simulates' : 'fails in simulator',
        run.simulation.ok ? 'ok' : 'bad'), `
        <div class="split">
          <div class="card"><ol class="reasoning">${run.procedure.map((s) => `<li>${esc(s)}</li>`).join('')}</ol></div>
          <div class="card">${plateMap(run.plate)}</div>
        </div>
        <div class="card"><pre><code>${esc(run.protocol)}</code></pre>
          <p class="muted">${esc(run.simulation.detail)}</p></div>`],
      ['Check against the held-out paper', pill(`${passed}/${v.checks.length} checks`, passed === v.checks.length ? 'ok' : 'bad'), `
        <div class="card"><p>${esc(v.held_out)}</p><p class="muted">${esc(v.truth)}</p>
          <ul class="checks">${v.checks.map(([text, ok]) => `<li><span class="${ok ? 'y' : 'n'}">${ok ? '✓' : '✗'}</span>${esc(text)}</li>`).join('')}</ul></div>`],
    ];
  }

  let shown = 0, list = [], timer = null;

  function reveal(n) {
    while (shown < Math.min(n, list.length)) {
      const [title, status, body] = list[shown++];
      const li = document.createElement('li');
      li.className = 'stage';
      li.innerHTML = `<h3>${esc(title)}${status}</h3>${body}`;
      $('timeline').append(li);
      if (!params.has('all')) li.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    $('controls').hidden = shown >= list.length;
  }

  function play(run, { all = false, auto = true } = {}) {
    clearInterval(timer);
    $('timeline').innerHTML = '';
    $('msg').hidden = true;
    $('mock').hidden = !run.mock;
    $('q').value = run.query;
    shown = 0;
    list = stages(run);
    if (all) return reveal(list.length);
    reveal(1);
    if (auto) timer = setInterval(() => { reveal(shown + 1); if (shown >= list.length) clearInterval(timer); }, STEP_MS);
  }

  // the trace for a typed query: an exact or near match among the predefined ones
  const words = (s) => new Set(s.toLowerCase().match(/[a-z0-9]+/g) || []);
  function find(query) {
    const q = words(query);
    let best = null, score = 0;
    for (const run of runs) {
      const w = words(run.query);
      const s = [...q].filter((x) => w.has(x)).length / Math.max(1, w.size);
      if (s > score) { best = run; score = s; }
    }
    return score >= 0.5 ? best : null;
  }

  $('ask').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const run = find($('q').value);
    if (run) return play(run);
    clearInterval(timer);
    $('timeline').innerHTML = '';
    $('controls').hidden = true;
    $('msg').hidden = false;
    $('msg').textContent = 'This static demo only plays its predefined queries; try one of the suggestions.';
  });
  $('next').addEventListener('click', () => { clearInterval(timer); reveal(shown + 1); });
  $('all').addEventListener('click', () => { clearInterval(timer); reveal(list.length); });
  $('suggest').innerHTML = runs.map((r, i) => `<button type="button" data-i="${i}">${esc(r.query)}</button>`).join('');
  $('suggest').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (b) play(runs[+b.dataset.i]);
  });

  const first = runs.find((r) => r.id === params.get('run')) || runs[0];
  if (first) {
    $('q').value = first.query;
    if (params.has('all')) play(first, { all: true });
  }
})();
