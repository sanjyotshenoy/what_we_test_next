// The demo page: plays one trace (runs/*.js, format in README.md) as a timeline of stages. Each stage first
// "works" (its title shimmers with what it is doing), then shows its pieces one at a time: a tool call shows a
// shimmering "running" tag before its result, reasoning streams in word by word. The finished stage then stays
// put for a reading pause sized to its text, while the next stage starts working below it. "Next step" finishes
// the current stage at once, "Show all" the whole run; ?all opens with everything shown.
// A query that matches no trace says so: the page is static until a backend serves traces, and then only find()
// needs to change.
(function () {
  'use strict';

  // pacing, in ms: tuned for an audience reading along
  const THINK = 2200;           // a stage's title shimmers this long before anything appears
  const RUN = 1300;             // a tool call's "running" tag, before its result
  const GAP = 650;              // between pieces of a stage
  const WORD = 55;              // streaming, per word
  const READ_PER_WORD = 110;    // the pause after a stage, per word of it...
  const READ_MIN = 1800, READ_MAX = 6500;   // ...within these bounds

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
  // a piece of a stage, shown in turn; `run` gives it a shimmering tag (e.g. "running") before its .res part
  const piece = (html, { run = '', tag = 'div', cls = '' } = {}) =>
    `<${tag} class="piece ${cls}"${run ? ` data-run="${esc(run)}"` : ''}>${html}</${tag}>`;

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

  // one entry per stage: { title, working (what the shimmer says), status (pill html), body (pieces) }
  function stages(run) {
    const e = run.proposal.experiment;
    const fields = [
      ['Assay', e.assay_type], ['Readout', e.readout], ['System', e.system],
      ['Series', `${e.top_concentration_uM} µM top, 1:${e.dilution_factor}, ${e.n_points} points`],
      ['Replicates', e.replicates], ['Controls', e.controls.join(' · ')],
    ];
    const v = run.validation;
    const passed = v.checks.filter(([, ok]) => ok).length;
    const stream = (items) => items.map((s) => piece(esc(s), { tag: 'li', cls: 'stream' })).join('');
    return [
      { title: 'Ask the knowledge base', working: 'Searching the knowledge base…',
        status: pill(run.lookup.verdict, 'unknown'),
        body: piece(`<div class="call">${callText(run.lookup.tool, run.lookup.args)}</div>
          <div class="res"><p>${esc(run.lookup.result)}</p><p class="muted">${esc(run.lookup.note)}</p></div>`,
          { run: 'searching', cls: 'card' }) },
      { title: 'Query the knowledge graphs', working: 'Calling the graph tools…', status: '',
        body: run.calls.map((c) => piece(`<div class="call">${callText(c.tool, c.args)}</div>
          <div class="res"><p class="muted">${esc(c.summary)}</p>${table(c.rows, c.columns)}</div>`,
          { run: 'running', cls: 'card' })).join('') },
      { title: 'Reason about the gap', working: 'Thinking…', status: '',
        body: `<div class="card"><ol class="reasoning">${stream(run.reasoning)}</ol></div>` },
      { title: 'Propose the missing experiment', working: 'Designing the experiment…', status: '',
        body: `<div class="card"><dl class="fields">${fields.map(([k, x]) =>
          piece(`<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`, { cls: 'pair' })).join('')}</dl>
          ${piece(run.proposal.citations.map((c) => `<span class="chip">${esc(c)}</span>`).join(''), { cls: 'chips' })}</div>` },
      { title: 'Write the procedure and the robot script', working: 'Writing the procedure and the OT-2 script…',
        status: pill(run.simulation.ok ? 'simulates' : 'fails in simulator', run.simulation.ok ? 'ok' : 'bad'),
        body: `<div class="split">
            <div class="card"><ol class="reasoning">${stream(run.procedure)}</ol></div>
            ${piece(plateMap(run.plate), { cls: 'card' })}
          </div>
          ${piece(`<pre><code>${esc(run.protocol)}</code></pre>
            <div class="res"><p class="muted">${esc(run.simulation.detail)}</p></div>`, { run: 'simulating', cls: 'card' })}` },
      { title: 'Check against the held-out paper', working: 'Comparing with the held-out record…',
        status: pill(`${passed}/${v.checks.length} checks`, passed === v.checks.length ? 'ok' : 'bad'),
        body: `<div class="card">${piece(`<p>${esc(v.held_out)}</p><p class="muted">${esc(v.truth)}</p>`)}
          <ul class="checks">${v.checks.map(([text, ok]) => piece(`<span class="${ok ? 'y' : 'n'}">${ok ? '✓' : '✗'}</span>${esc(text)}`,
            { tag: 'li' })).join('')}</ul></div>` },
    ];
  }

  // Playback. `token` changes when a new run starts, which stops the old one at its next wait; `hurry` makes
  // every wait instant (1 = finish this stage, 2 = finish the run).
  let token = 0, hurry = 0, list = [], shown = 0, wake = null;
  const sleep = (ms, t) => (hurry || t !== token ? Promise.resolve() : new Promise((r) => {
    const id = setTimeout(r, ms);
    wake = () => { clearTimeout(id); r(); };   // so Next step / Show all cut a wait short
  }));
  const rush = (level) => { hurry = Math.max(hurry, level); if (wake) wake(); };
  const follow = (el) => { if (!hurry) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); };

  async function streamText(el, t) {
    const words = el.textContent.split(/(\s+)/);
    el.textContent = '';
    for (let i = 0; i < words.length; i += 2) {
      if (t !== token) return;
      el.textContent += words[i] + (words[i + 1] || '');
      if (!hurry) await sleep(WORD, t);
    }
  }

  async function playStage(stage, t) {
    const li = document.createElement('li');
    li.className = 'stage working';
    li.innerHTML = `<h3><span class="title">${esc(stage.title)}</span><span class="status"></span></h3>
      <p class="doing shine">${esc(stage.working)}</p>${stage.body}`;
    $('timeline').append(li);
    follow(li);
    await sleep(THINK, t);
    li.classList.remove('working');
    for (const p of li.querySelectorAll('.piece')) {
      if (t !== token) return;
      p.classList.add('in');
      follow(p);
      if (p.dataset.run) {
        p.insertAdjacentHTML('afterbegin', `<span class="runtag shine">${esc(p.dataset.run)}…</span>`);
        await sleep(RUN, t);
        p.querySelector('.runtag').remove();
        p.classList.add('done');
        follow(p);
      }
      if (p.classList.contains('stream')) await streamText(p, t);
      await sleep(GAP, t);
    }
    li.querySelector('.status').innerHTML = stage.status;
    const words = li.textContent.split(/\s+/).length;
    await sleep(Math.min(READ_MAX, Math.max(READ_MIN, words * READ_PER_WORD)), t);
  }

  async function play(run, { all = false } = {}) {
    const t = ++token;
    if (wake) wake();
    hurry = all ? 2 : 0;
    $('timeline').innerHTML = '';
    $('msg').hidden = true;
    $('mock').hidden = !run.mock;
    $('q').value = run.query;
    list = stages(run);
    $('controls').hidden = all;
    for (shown = 0; shown < list.length; shown++) {
      if (t !== token) return;
      await playStage(list[shown], t);
      if (hurry === 1) hurry = 0;
    }
    if (t === token) $('controls').hidden = true;
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
    token++;
    if (wake) wake();
    $('timeline').innerHTML = '';
    $('controls').hidden = true;
    $('msg').hidden = false;
    $('msg').textContent = 'This static demo only plays its predefined queries; try one of the suggestions.';
  });
  $('next').addEventListener('click', () => rush(1));
  $('all').addEventListener('click', () => rush(2));
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
