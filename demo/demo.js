// The demo page: plays one trace (runs/*.js, format in README.md) as a timeline of stages. Each stage first
// "works" (its title shimmers with what it is doing), then shows its pieces one at a time: a tool call shows a
// shimmering "running" tag before its result, reasoning streams in word by word. The finished stage then waits:
// "Next step" starts the next stage (pressed while a stage is still playing, it finishes that stage first).
// "Show all" plays the whole run at once; ?all opens with everything shown; ?auto plays on by itself instead,
// pausing after each stage for a reading time sized to its text.
//
// Two sources of traces, played by the same code:
// - static: the runs/*.js files loaded by index.html (a recorded run, or a mock), all data there from the start;
// - live: the backend of agent/server.py (`python -m agent.server`), which runs the agent on the typed question
//   and streams the trace stage by stage. The page looks for it at /api/health (or ?api=<base url>); when it is
//   there, "Run live" and a model dropdown appear and typed questions go to it. Pieces play as they arrive; a stage whose data never
//   comes (e.g. no execution/ yet) is skipped. If the live run fails before showing anything, the recorded trace
//   for that question plays instead.
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
  // theme: ?theme=dark|light, else the one chosen with the button last time, else the system's
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem('demo-theme'); } catch (e) { /* private window, blocked storage */ }
  if (params.get('theme') || saved) root.dataset.theme = params.get('theme') || saved;
  const theme = () => root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const showTheme = () => { document.getElementById('theme').textContent = theme() === 'dark' ? '☀ Light' : '☾ Dark'; };
  document.getElementById('theme').addEventListener('click', () => {
    root.dataset.theme = theme() === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('demo-theme', root.dataset.theme); } catch (e) { /* ignore */ }
    showTheme();
  });
  showTheme();
  const API = (params.get('api') || '').replace(/\/$/, '');   // '' = same origin as the page
  const AUTO = params.has('auto');                             // play on without waiting for "Next step"
  let live = null;                                             // {model, graphs} once the backend answered

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const callText = (tool, args) => `${esc(tool)}(${Object.entries(args || {})
    .map(([k, v]) => `<span class="arg">${esc(k)}=</span>${esc(JSON.stringify(v))}`).join(', ')})`;
  const table = (rows, columns) => rows && rows.length ? `<div class="table-wrap"><table>${columns
    ? `<tr>${columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>` : ''}${rows
    .map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table></div>` : '';
  const pill = (text, kind) => `<span class="pill ${kind}">${esc(text)}</span>`;
  // a piece of a stage, shown in turn; `run` gives it a shimmering tag (e.g. "running") before its .res part
  const piece = (html, { run = '', tag = 'div', cls = '' } = {}) =>
    `<${tag} class="piece ${cls}"${run ? ` data-run="${esc(run)}"` : ''}>${html}</${tag}>`;
  const stream = (s) => piece(esc(s), { tag: 'li', cls: 'stream' });

  // the wells: a 1:factor series across columns 1..points of the given rows, darker = more compound
  function plateMap(p) {
    const cols = Array.from({ length: 12 }, (_, i) => i + 1);
    const fill = (r, c) => {
      if (!p.rows.includes(r)) return '';
      if (c <= p.points) return `background: color-mix(in srgb, var(--accent) ${Math.round(100 - 85 * (c - 1) / Math.max(1, p.points - 1))}%, transparent)`;
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

  // --- figures: inline SVG drawn from the trace's own data, so they follow the run and the theme ---------
  const num = (s) => { const m = String(s).match(/([\d.]+)\s*(nM|µM|μM|uM)/i); return m ? +m[1] * (/^n/i.test(m[2]) ? 1 : 1000) : null; };   // in nM
  const fmtC = (nM) => (nM >= 1000 ? `${+(nM / 1000).toPrecision(2)} µM` : `${+nM.toPrecision(2)} nM`);
  const svgText = (x, y, s, cls = '', anchor = 'middle') => `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${esc(s)}</text>`;
  // a node box: the name on one line, or two when it is long, and the ID under it in monospace
  const wrap = (name, max = 19) => {
    if (name.length <= max) return [name];
    const cut = name.lastIndexOf(' ', max);
    return cut > 4 ? [name.slice(0, cut), name.slice(cut + 1)] : [name.slice(0, max - 1) + '…'];
  };
  const node = (x, y, w, name, id, kind) => {
    const lines = wrap(name), h = lines.length > 1 ? 54 : 40, top = y - h / 2;
    return `<g class="node ${kind}"><rect x="${x - w / 2}" y="${top}" width="${w}" height="${h}" rx="8"/>
      ${lines.map((l, i) => svgText(x, top + 17 + i * 14, l.length > 24 ? l.slice(0, 23) + '…' : l)).join('')}${svgText(x, top + h - 7, id, 'id')}</g>`;
  };
  // an edge with its label near the start (for the fan of edges into one node) or above the gap between columns
  const edge = (x1, y1, x2, y2, label = '', cls = 'edge', where = 'start') =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="${cls}" marker-end="url(#arr)"/>`
    + (!label ? '' : where === 'start'
      ? svgText(x1 + 8, y1 + (y2 - y1) * 0.1 + (cls === 'gap' || y2 < y1 ? -6 : 13), label, `small ${cls === 'gap' ? 'gap' : 'muted'}`, 'start')
      : svgText((x1 + x2) / 2, Math.min(y1, y2) - 30, label, 'small muted'));

  // the part of the two graphs the run touched: compound and analogs | target | class | protocol | its format,
  // endpoint and readout. The missing edge, compound → target, is the gap the experiment fills.
  function subgraphFig(run) {
    const by = Object.fromEntries(run.calls.map((c) => [c.tool, c]));
    const res = by['bio_kg.resolve'], ana = by['bio_kg.analogs'], tpl = by['protocol_kg.templates'];
    if (!res) return '';
    const ofType = (rows, t) => (rows || []).filter((r) => r[1] === t);
    const comp = ofType(res.rows, 'Compound')[0], targ = ofType(res.rows, 'Target')[0], cls = ofType(res.rows, 'TargetClass')[0];
    if (!comp || !targ) return '';
    const analogs = (ana ? ana.rows : []).map((r) => {
      const m = String(r[0]).match(/^(.*?)\s*\(([^)]+)\)\s*$/);
      return { name: m ? m[1] : String(r[0]), id: m ? m[2] : '', sim: r[1], ic50: r[2] };
    });
    const proto = tpl ? ofType(tpl.rows, 'Protocol')[0] : null;
    const extras = tpl ? tpl.rows.filter((r) => ['Format', 'Endpoint', 'Readout'].includes(r[1])) : [];
    const left = [{ id: comp[0], name: comp[2], kind: 'compound' },
      ...analogs.map((a) => ({ id: `${a.id}${a.sim && a.sim !== 'n/a' ? ` · sim ${a.sim}` : ''}`, name: a.name, kind: 'analog', ic50: a.ic50 }))];
    const rows = Math.max(left.length, extras.length, 1);
    const DY = 64, TOP = 40, H = TOP + rows * DY, W = 960;
    const X = [104, 356, 548, 738, 892], BW = [184, 140, 120, 150, 112];   // column centres and box widths
    const yOf = (i, n) => TOP + (i + 0.5 + (rows - n) / 2) * DY;
    const yMid = yOf(0, 1);
    const R = (c) => X[c] + BW[c] / 2, L = (c) => X[c] - BW[c] / 2;   // a column's right and left box edges
    let s = `<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" class="arrow"/></marker></defs>`;
    // edges first, under the nodes
    left.forEach((n, i) => {
      const y = yOf(i, left.length);
      s += n.kind === 'compound'
        ? edge(R(0), y, L(1), yMid, 'no measurement', 'gap')
        : edge(R(0), y, L(1), yMid, String(n.ic50));   // just the IC50 value: short enough to clear the other lines
    });
    if (cls) s += edge(R(1), yMid, L(2), yMid, 'member of', 'edge', 'above');
    if (cls && proto) s += edge(L(3), yMid, R(2), yMid, 'applicable to', 'edge', 'above');
    if (proto) extras.forEach((r, i) => { s += edge(R(3), yMid, L(4), yOf(i, extras.length)); });
    // nodes
    left.forEach((n, i) => { s += node(X[0], yOf(i, left.length), BW[0], n.name, n.id, n.kind); });
    s += node(X[1], yMid, BW[1], targ[2].replace(/\s*\(.*$/, ''), targ[0], 'target');
    if (cls) s += node(X[2], yMid, BW[2], cls[2], cls[0], 'class');
    if (proto) s += node(X[3], yMid, BW[3], proto[2].split(',')[0], proto[0], 'protocol');
    extras.forEach((r, i) => { s += node(X[4], yOf(i, extras.length), BW[4], r[2], r[1].toLowerCase(), 'extra'); });
    const heads = [['biology KG', (X[0] + X[1]) / 2], ['bridge', X[2]], ['protocol KG', (X[3] + X[4]) / 2]];
    s += heads.map(([t, x]) => svgText(x, 14, t, 'small muted')).join('');
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="The subgraph the agent used">${s}</svg>
      <p class="cap">What the agent touched in the two graphs. The dashed edge is the measurement nobody has made; the
      target's class bridges the biology graph to the protocol graph.</p>`;
  }

  // the proposed series on a log axis, against the analogs' IC50s: does it bracket the expected potency?
  function rangeFig(run) {
    const e = run.proposal && run.proposal.experiment;
    if (!e || !e.n_points || !e.dilution_factor) return '';
    const ana = run.calls.find((c) => c.tool === 'bio_kg.analogs');
    const analogs = (ana ? ana.rows : []).map((r) => ({ name: String(r[0]).replace(/\s*\(.*$/, ''), nM: num(r[2]) }))
      .filter((a) => a.nM).sort((a, b) => a.nM - b.nM);
    const series = Array.from({ length: e.n_points }, (_, i) => e.top_concentration_uM * 1000 / e.dilution_factor ** i);
    const all = [...series, ...analogs.map((a) => a.nM)];
    const lo = Math.floor(Math.log10(Math.min(...all)) - 0.2), hi = Math.ceil(Math.log10(Math.max(...all)) + 0.2);
    const W = 760, H = 132, x0 = 28, x1 = 732, AX = 92;
    const X = (nM) => x0 + (Math.log10(nM) - lo) / (hi - lo) * (x1 - x0);
    let s = `<line x1="${x0}" y1="${AX}" x2="${x1}" y2="${AX}" class="axis"/>`;
    for (let d = lo; d <= hi; d++) {
      s += `<line x1="${X(10 ** d)}" y1="${AX}" x2="${X(10 ** d)}" y2="${AX + 6}" class="axis"/>` + svgText(X(10 ** d), AX + 20, fmtC(10 ** d), 'small muted');
    }
    let below = null, above = null;
    if (analogs.length) {
      const a = analogs[0].nM, b = analogs[analogs.length - 1].nM;
      s += `<rect x="${X(a) - 6}" y="28" width="${X(b) - X(a) + 12}" height="${AX - 28}" rx="4" class="band"/>`
        + svgText((X(a) + X(b)) / 2, 22, 'expected potency, from the analogs', 'small muted');
      analogs.forEach((an, i) => {
        const y = 48 + (i % 2) * 16;
        s += `<circle cx="${X(an.nM)}" cy="${y}" r="4" class="ana"/>` + svgText(X(an.nM) + 7, y + 4, `${an.name} ${fmtC(an.nM)}`, 'small', 'start');
      });
      below = series.filter((c) => c < a).length;
      above = series.filter((c) => c > b).length;
    }
    series.forEach((c) => { s += `<circle cx="${X(c)}" cy="${AX}" r="5" class="pt"/>`; });
    s += svgText(X(series[0]), AX - 12, `${fmtC(series[0])} top`, 'small', 'end') + svgText(X(series[series.length - 1]), AX - 12, fmtC(series[series.length - 1]), 'small', 'start');
    const cap = `${e.n_points} points, 1:${e.dilution_factor}` + (below === null ? '' : `: ${below} below and ${above} above the analogs' range`)
      + (below !== null && (below < 2 || above < 2) ? ' (fewer than two on one side)' : '');
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="The proposed concentration series">${s}</svg><p class="cap">${esc(cap)}.</p>`;
  }

  // The stages, in order. Each says when it can start (`ready`), when nothing more will come (`complete`), and
  // gives its pieces as a list of html chunks (`pieces`), appended into `body` as they appear; `status` is the
  // pill shown once the stage is done. A run is "finished" when its source says so (static: at once).
  const STAGES = [
    { title: 'Ask the knowledge base', working: 'Searching the knowledge base…',
      ready: (r) => !!r.lookup, complete: (r) => !!r.lookup,
      status: (r) => pill(r.lookup.verdict, r.lookup.verdict === 'answered' ? 'ok' : 'unknown'),
      pieces: (r) => [piece(`<div class="call">${callText(r.lookup.tool, r.lookup.args)}</div>
          <div class="res"><p>${esc(r.lookup.result)}</p>${table(r.lookup.rows)}${r.lookup.note ? `<p class="muted">${esc(r.lookup.note)}</p>` : ''}</div>`,
        { run: 'searching', cls: 'card' })] },
    { title: 'Query the knowledge graphs', working: 'Calling the graph tools…',
      ready: (r) => r.calls.length > 0, complete: (r) => r.finished || !!r.proposal,
      status: () => '',
      pieces: (r) => {
        const calls = r.calls.map((c) => piece(`<div class="call">${callText(c.tool, c.args)}</div>
          <div class="res"><p class="muted">${esc(c.summary)}</p>${table(c.rows, c.columns)}</div>`, { run: 'running', cls: 'card' }));
        const fig = (r.finished || r.proposal) ? subgraphFig(r) : '';   // once every call is in
        return fig ? [...calls, piece(fig, { cls: 'card fig' })] : calls;
      } },
    { title: 'Reason about the gap', working: 'Thinking…',
      ready: (r) => r.reasoning.length > 0, complete: (r) => r.finished || !!r.proposal,
      status: () => '', body: '<div class="card"><ol class="reasoning" data-body></ol></div>',
      pieces: (r) => r.reasoning.map(stream) },
    { title: 'Propose the missing experiment', working: 'Designing the experiment…',
      ready: (r) => !!(r.proposal && r.proposal.experiment), complete: (r) => !!r.proposal,
      status: () => '',
      pieces: (r) => {
        const e = r.proposal.experiment;
        const fields = [
          ['Assay', e.assay_type], ['Readout', e.readout], ['System', e.system],
          ['Series', `${e.top_concentration_uM} µM top, 1:${e.dilution_factor}, ${e.n_points} points`],
          ['Replicates', e.replicates], ['Controls', (e.controls || []).join(' · ')],
        ];
        const fig = rangeFig(r);
        return [`<div class="card"><dl class="fields">${fields.map(([k, x]) =>
          piece(`<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`, { cls: 'pair' })).join('')}</dl>
          ${piece((r.proposal.citations || []).map((c) => `<span class="chip">${esc(c)}</span>`).join(''), { cls: 'chips' })}</div>`
          + (fig ? piece(fig, { cls: 'card fig' }) : '')];
      } },
    { title: 'Write the procedure and the robot script', working: 'Writing the procedure and the OT-2 script…',
      ready: (r) => !!(r.procedure && r.protocol && r.simulation), complete: (r) => !!(r.procedure && r.protocol && r.simulation),
      status: (r) => pill(r.simulation.ok ? 'simulates' : 'fails in simulator', r.simulation.ok ? 'ok' : 'bad'),
      pieces: (r) => [`<div class="split">
            <div class="card"><ol class="reasoning">${r.procedure.map(stream).join('')}</ol></div>
            ${r.plate ? piece(plateMap(r.plate), { cls: 'card' }) : ''}
          </div>
          ${piece(`<pre><code>${esc(r.protocol)}</code></pre>
            <div class="res"><p class="muted">${esc(r.simulation.detail)}</p></div>`, { run: 'simulating', cls: 'card' })}`] },
    { title: 'Check against the held-out paper', working: 'Comparing with the held-out record…',
      ready: (r) => !!r.validation, complete: (r) => !!r.validation,
      status: (r) => { const n = r.validation.checks.filter(([, ok]) => ok).length;
        return pill(`${n}/${r.validation.checks.length} checks`, n === r.validation.checks.length ? 'ok' : 'bad'); },
      pieces: (r) => [`<div class="card">${piece(`<p>${esc(r.validation.held_out)}</p><p class="muted">${esc(r.validation.truth)}</p>`)}
          <ul class="checks">${r.validation.checks.map(([text, ok]) => piece(`<span class="${ok ? 'y' : 'n'}">${ok ? '✓' : '✗'}</span>${esc(text)}`,
            { tag: 'li' })).join('')}</ul></div>`] },
  ];

  // Playback. `token` changes when a new run starts, which stops the old one at its next wait; `hurry` makes
  // every wait instant (1 = finish this stage, 2 = finish the run). `changed()` wakes whoever waits for more
  // data from a live run.
  let token = 0, hurry = 0, wake = null, waiters = [], nextClick = null;
  const sleep = (ms, t) => (hurry || t !== token ? Promise.resolve() : new Promise((r) => {
    const id = setTimeout(r, ms);
    wake = () => { clearTimeout(id); r(); };   // so Next step / Show all cut a wait short
  }));
  const stepOn = () => { if (nextClick) { const r = nextClick; nextClick = null; r(); } };
  const rush = (level) => { hurry = Math.max(hurry, level); if (wake) wake(); stepOn(); };
  // after a stage: wait for "Next step" (unless showing all, or ?auto)
  const waitNext = (t) => (hurry === 2 || t !== token ? Promise.resolve() : new Promise((r) => { nextClick = r; }));
  const follow = (el) => { if (!hurry) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); };
  const changed = () => { const w = waiters; waiters = []; w.forEach((r) => r()); };
  const moreData = () => new Promise((r) => waiters.push(r));

  async function streamText(el, t) {
    const words = el.textContent.split(/(\s+)/);
    el.textContent = '';
    for (let i = 0; i < words.length; i += 2) {
      if (t !== token) return;
      el.textContent += words[i] + (words[i + 1] || '');
      if (!hurry) await sleep(WORD, t);
    }
  }

  // plays every piece of the stage not yet played, in document order
  async function playPieces(li, t) {
    for (const p of li.querySelectorAll('.piece:not(.played)')) {
      if (t !== token) return;
      p.classList.add('played', 'in');
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
  }

  // one stage: open it working, wait for its data, play pieces as they come, then its status and a reading pause
  async function playStage(stage, run, t) {
    const li = document.createElement('li');
    li.className = 'stage working';
    li.innerHTML = `<h3><span class="title">${esc(stage.title)}</span><span class="status"></span></h3>
      <p class="doing shine">${esc(stage.working)}</p>${stage.body || '<div data-body></div>'}`;
    $('timeline').append(li);
    follow(li);
    const body = li.querySelector('[data-body]'), doing = li.querySelector('.doing');
    const started = Date.now();
    while (!stage.ready(run)) {              // live: the data is still on its way
      if (t !== token) return;
      if (run.finished) { li.remove(); return; }   // nothing came for this stage: skip it
      $('next').disabled = true;             // nothing to skip to until the model answers
      await moreData();
      $('next').disabled = false;
    }
    await sleep(Math.max(0, THINK - (Date.now() - started)), t);
    if (t !== token) return;
    li.classList.remove('working');
    let shown = 0;
    for (;;) {
      const chunks = stage.pieces(run);
      if (chunks.length > shown) {
        body.insertAdjacentHTML('beforeend', chunks.slice(shown).join(''));
        shown = chunks.length;
        await playPieces(li, t);
        if (t !== token) return;
      }
      if (stage.complete(run) && stage.pieces(run).length === shown) break;
      // live: the rest of this stage is still being produced; say so, and "Next step" cannot skip the wait
      doing.textContent = `${stage.working.replace(/…$/, '')} (waiting for the model)…`;
      li.classList.add('waiting');
      $('next').disabled = true;
      await moreData();
      li.classList.remove('waiting');
      $('next').disabled = false;
      if (t !== token) return;
    }
    li.querySelector('.status').innerHTML = stage.status(run);
    if (AUTO) {
      const words = li.textContent.split(/\s+/).length;
      await sleep(Math.min(READ_MAX, Math.max(READ_MIN, words * READ_PER_WORD)), t);
    }
  }

  function badges(run, mode) {
    $('mock').hidden = !run.mock;
    $('live').hidden = mode !== 'live';
    if (mode === 'live') $('live').textContent = `Live · ${run.model}`;
    $('note').hidden = !run.note;
    $('note').textContent = run.note || '';
  }

  async function play(run, { all = false, mode = 'static' } = {}) {
    const t = ++token;
    if (wake) wake();
    stepOn();
    changed();
    hurry = all ? 2 : 0;
    $('timeline').innerHTML = '';
    $('msg').hidden = true;
    $('q').value = run.query;
    badges(run, mode);
    $('controls').hidden = all;
    for (const [i, stage] of STAGES.entries()) {
      if (t !== token) return;
      if (run.finished && !stage.ready(run)) continue;
      await playStage(stage, run, t);
      if (hurry === 1) hurry = 0;
      if (t !== token) return;
      // wait for "Next step", unless no later stage can still appear
      const more = STAGES.slice(i + 1).some((s) => s.ready(run) || !run.finished);
      if (!AUTO && more) { $('controls').classList.add('waiting'); await waitNext(t); $('controls').classList.remove('waiting'); }
    }
    if (t !== token) return;
    $('controls').hidden = true;
    if (run.error) { $('msg').hidden = false; $('msg').textContent = `The live run stopped: ${run.error}`; }
  }

  // a run object the stages read, filled from a live event stream
  function emptyRun(query, model) {
    return { id: '', query, model, mock: false, note: '', lookup: null, calls: [], reasoning: [], proposal: null,
      plate: null, finished: false, error: '' };
  }

  async function playLive(query) {
    const t = ++token;
    let res;
    try {
      res = await fetch(`${API}/api/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, model: $('model').value || undefined, fresh: params.has('fresh') }) });
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    } catch (e) {
      return fallback(query, `The live backend did not answer (${e.message}).`);
    }
    if (t !== token) return;
    const { id, model, cached } = await res.json();
    const run = emptyRun(query, model);
    run.note = cached ? 'Replaying this question’s earlier live run' : '';
    const es = new EventSource(`${API}/api/runs/${id}/events`);
    const on = (name, fn) => es.addEventListener(name, (ev) => { if (token !== t + 1) { es.close(); return; } fn(JSON.parse(ev.data)); changed(); });
    on('lookup', (d) => { run.lookup = d; });
    on('call', (d) => { run.calls.push(d); });
    on('reasoning', (d) => { run.reasoning.push(d); });
    on('proposal', (d) => { run.proposal = d; });
    on('plate', (d) => { run.plate = d; });
    on('error', (d) => { run.error = d.message; run.finished = true; es.close(); });
    on('done', () => { run.finished = true; es.close(); });
    es.onerror = () => { if (es.readyState === EventSource.CLOSED) { run.finished = true; changed(); } };
    await play(run, { mode: 'live' });   // bumps token to t + 1
  }

  function fallback(query, why) {
    const run = find(query);
    $('msg').hidden = false;
    $('msg').textContent = why + (run ? ' Playing the recorded run instead.' : '');
    if (run) play(run);
  }

  // the trace for a typed query: an exact or near match among the predefined ones (a real run before a mock)
  const words = (s) => new Set(s.toLowerCase().match(/[a-z0-9]+/g) || []);
  function find(query) {
    const q = words(query);
    let best = null, score = 0;
    for (const run of [...runs].sort((a, b) => (a.mock ? 1 : 0) - (b.mock ? 1 : 0))) {
      const w = words(run.query);
      const s = [...q].filter((x) => w.has(x)).length / Math.max(1, w.size);
      if (s > score) { best = run; score = s; }
    }
    return score >= 0.5 ? best : null;
  }

  $('ask').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const query = $('q').value.trim();
    if (live && $('golive').checked && query) return playLive(query);
    const run = find(query);
    if (run) return play(run);
    token++;
    if (wake) wake();
    $('timeline').innerHTML = '';
    $('controls').hidden = true;
    $('msg').hidden = false;
    $('msg').textContent = live ? 'No recorded run for that question: tick “Run live” to ask the agent.'
      : 'This static demo only plays its predefined queries; try one of the suggestions.';
  });
  $('next').addEventListener('click', () => (nextClick ? stepOn() : rush(1)));
  $('all').addEventListener('click', () => rush(2));
  $('suggest').innerHTML = runs.map((r, i) => `<button type="button" data-i="${i}">${esc(r.query)}${r.mock ? ' <span class="muted">· mock</span>' : ''}</button>`).join('');
  $('suggest').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (b) play(runs[+b.dataset.i]);
  });

  runs.forEach((r) => { r.finished = true; r.calls = r.calls || []; r.reasoning = r.reasoning || []; });
  const first = runs.find((r) => r.id === params.get('run')) || runs[0];
  if (first) {
    $('q').value = first.query;
    if (params.has('all')) play(first, { all: true });
  }

  // is the live backend there? (not from file://, and not with ?static)
  if (!params.has('static') && (API || location.protocol.startsWith('http'))) {
    fetch(`${API}/api/health`).then((r) => r.ok ? r.json() : null).then((h) => {
      if (!h || !h.ok) return;
      live = h;
      const models = [...new Set([params.get('model'), ...(h.models || [h.model])].filter(Boolean))];
      $('model').innerHTML = models.map((m) => `<option value="${esc(m)}">${esc(m.split('/').pop())}</option>`).join('');
      $('model').value = params.get('model') || h.model;
      $('livebox').hidden = false;
      $('golive').checked = true;
      $('q').placeholder = 'Ask a question the literature can’t answer yet… (runs the agent live)';
    }).catch(() => {});
  }
})();
