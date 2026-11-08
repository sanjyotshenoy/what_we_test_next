/* Saved artifact walkthrough, not a transcript or a wall-clock reconstruction.
   Only the existing published-session API is used; no operator endpoints. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const detail = (title, value) => `<details><summary>${esc(title)}</summary><pre>${esc(typeof value === 'string' ? value : JSON.stringify(value, null, 2))}</pre></details>`;
  const card = content => `<div class="card record">${content}</div>`;
  const paragraph = text => `<p>${esc(text)}</p>`;
  let modelCatalog = {models: [], sessions: {}}, recordings = [], selected = null, stages = [], cursor = 0, timer = null, paused = false;
  const api = async path => { const r = await fetch(path); if (!r.ok) throw new Error(`Could not load saved results (${r.status}).`); return r.json(); };
  function stopTimer() { clearTimeout(timer); timer = null; }
  function schedule() {
    stopTimer();
    if (!paused && cursor < stages.length) timer = setTimeout(advance, 3500);
  }
  function controls() {
    $('message').textContent = cursor >= stages.length ? 'Experiment plan and simulation results ready.' : `${paused ? 'Paused · ' : ''}${stages[Math.max(0, cursor - 1)]?.title || 'Preparing example'}`;
  }
  function collapseLongText(container) {
    for (const el of container.querySelectorAll('p, pre')) {
      const full = el.textContent;
      const words = [...full.matchAll(/\S+/g)];
      // Preserve links and other markup; these short navigational paragraphs
      // are not prose bodies. Text-only paragraphs and raw details are safe.
      if (words.length <= 100 || el.children.length) continue;
      const last = words[99];
      const preview = full.slice(0, last.index + last[0].length) + '…';
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'quiet expand-text';
      button.textContent = 'Show more'; button.setAttribute('aria-expanded', 'false');
      el.textContent = preview;
      button.onclick = () => {
        const expand = button.getAttribute('aria-expanded') !== 'true';
        el.textContent = expand ? full : preview;
        button.textContent = expand ? 'Show less' : 'Show more';
        button.setAttribute('aria-expanded', String(expand));
      };
      el.after(button);
    }
  }
  function advance() {
    stopTimer();
    if (cursor >= stages.length) return;
    const stage = stages[cursor++];
    const li = document.createElement('li'); li.className = 'stage';
    li.innerHTML = `<h3>${esc(stage.title)}</h3>${stage.html}`;
    collapseLongText(li);
    $('timeline').append(li); controls(); schedule();
    li.style.scrollMarginTop = '16px';
    li.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start'});
  }
  function evidenceSummary(e) {
    const r = e.result || {};
    if (e.tool === 'planning_context') return paragraph(r.template?.purpose || 'Saved protocol context and compiler capabilities loaded.');
    if (e.tool === 'literature_search') return (r.papers || []).map(p=>paragraph(`${p.document_id}: ${p.title}`)).join('') + paragraph(r.note || '');
    if (e.tool === 'literature_read') return paragraph(r.passage || r.note || '');
    if (e.tool === 'biology_lookup') return paragraph([...(r.compound_matches || []), ...(r.species_matches || [])].map(x=>`${x.name} (${x.id})`).join(' → ')) +
      (r.measurements || []).map(m=>paragraph(`MIC ${m.props?.relation || ''} ${m.props?.mic} ${m.props?.unit} · assay ${m.props?.assay} · document ${m.props?.document}`)).join('') +
      paragraph(`Showing ${r.measurements?.length || 0} saved measurements; ${r.total_measurements ?? 'unknown'} total matches. Original units preserved; these values are background evidence, not chosen assay settings.`);
    return '';
  }
  function build(data) {
    const out = [{title:'Plan the experiment', html:card(paragraph('Follow the stack as it gathers evidence, proposes an experiment, generates OT-2 protocols and checks them in the simulator.') + detail('About this example', 'Precomputed model and tool outputs, presented step by step. Assay settings are synthetic test inputs. Simulation is a software check, not a physical experiment or biological validation; pacing does not reproduce original tool durations.'))}];
    for (const e of data.evidence || []) {
      const r = e.result || {};
      const titles = {planning_context:'Load protocol context', biology_lookup:'Look up biological evidence', literature_search:'Search the literature', literature_read:'Read a retrieved passage'};
      out.push({title:titles[e.tool] || e.tool, html:card(`<div class="call">${esc(e.tool)}</div>` + paragraph(e.retrieved_at || '') + detail('Recorded tool inputs', e.args) + evidenceSummary(e) + detail('Recorded tool result', r))});
    }
    for (const b of data.batches || []) {
      const m = b.manifest;
      for (const c of b.batch?.compounds || []) {
        const p = c.proposal, e = p.experiment || {};
        out.push({title:`Propose an experiment · ${c.compound}`, html:card(paragraph(p.rationale) + `<dl class="fields">${[['Assay',e.assay_type],['Panel',(e.panel || []).map(s=>s.name).join(', ')],['Series',`${e.top_concentration ?? e.top_concentration_uM} ${e.concentration_unit || 'uM'}; 1:${e.dilution_factor}; ${e.n_points} points`],['Replicates',e.replicates],['Controls',(e.controls||[]).join(', ')]].map(([k,v])=>`<div class="pair in"><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>` + detail('Saved proposal and citations',p) + detail('Parameter provenance',c.evidence_links))});
      }
      out.push({title:'Inspect compiler rule checks',html:card(detail('Saved rule results',b.rules) + paragraph('These are software checks; they are not held-out benchmark grading or domain review.'))});
      for (const run of m.runs || []) {
        const snapshot = b.runs.find(r=>r.run_id===run.run_id);
        const base = `/api/artifacts/${encodeURIComponent(data.session)}/${encodeURIComponent(m.batch_id)}/${encodeURIComponent(run.run_id)}/`;
        out.push({title:`Compile ${run.run_id} · ${run.compound} / ${run.species?.name || ''}`,html:card(paragraph('A separate OT-2 protocol was generated for this compound–species pair.') + `<p><a href="${base}protocol.py">Download protocol</a> · <a href="${base}run_sheet.md">Run sheet</a> · <a href="${base}plate.json">Plate map</a></p>` + detail('Sources and well layout',{sources:snapshot?.sources,plate:snapshot?.plate}) + detail('Compiler warnings',run.warnings || []))});
        const pass = !!snapshot?.simulation && run.simulation?.status === 'passed';
        out.push({title:`Simulator result · ${run.run_id}`,html:card(`<p class="${pass ? 'ok' : 'bad'}">${pass ? 'Saved simulation passed (protocol hash verified by the viewer).' : 'No verified simulation pass available.'}</p>` + detail('Saved simulator report',snapshot?.simulation || run.simulation) + paragraph('No physical execution or biological outcome is implied.'))});
      }
    }
    out.push({title:'Review the experiment plan',html:card(paragraph('The experiment plan, generated protocols and simulation results are ready to inspect. Strain selection, evidence applicability and physical execution remain separate review steps.') + '<a href="/">Open the full results viewer</a>')});
    return out;
  }
  function start(index) {
    stopTimer(); selected=index; cursor=0; paused=false;
    const data=recordings[index]; stages=build(data); $('timeline').replaceChildren();
    $('provenance').textContent=`Precomputed example · model and tool outputs · ${data.session}`;
    for (const b of $('queries').querySelectorAll('button')) b.setAttribute('aria-pressed',String(Number(b.dataset.index)===index));
    advance();
  }
  $('theme').onclick=()=>{const root=document.documentElement;root.dataset.theme=(root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'))==='dark'?'light':'dark';};
  $('queries').onclick=e=>{const b=e.target.closest('button');if(b)start(Number(b.dataset.index));};
  function renderQueries() {
    stopTimer(); selected=null; stages=[]; cursor=0; paused=true;
    $('timeline').replaceChildren(); $('provenance').textContent='';
    const visible=recordings.map((r,i)=>({r,i})).filter(({r})=>modelCatalog.sessions[r.session]===$('llm').value);
    $('queries').innerHTML=visible.map(({r,i})=>{
      const runs=r.batches.flatMap(b=>b.manifest.runs || []);
      const compounds=[...new Set(runs.map(x=>x.compound))].join(' + ');
      const species=[...new Set(runs.map(x=>x.species?.name).filter(Boolean))].join(' + ');
      return `<button data-index="${i}" aria-pressed="false"><strong>Plan MIC experiments: ${esc(compounds)}</strong>${esc(species)}<small>Example query · ${runs.length} generated protocols</small></button>`;
    }).join('');
    $('message').textContent=visible.length?'Choose an example query to see the workflow.':'Trajectories for this model have not been precomputed and published yet.';
  }
  $('llm').onchange=renderQueries;
  (async()=>{
    try {
      const sessions=await api('/api/planning/sessions');
      recordings=await Promise.all(sessions.map(s=>api(`/api/planning?session=${encodeURIComponent(s.session)}`)));
      recordings=recordings.filter(r=>r.batches?.length);
      modelCatalog=await api('/sequential-assets/sequential-models.json');
      $('llm').innerHTML=modelCatalog.models.map(m=>`<option value="${esc(m.id)}">${esc(m.label)}</option>`).join('');
      $('llm').disabled=false;
      renderQueries();
    } catch(e) { $('message').textContent=e.message+' Reload to retry. No live fallback was started.'; }
  })();
})();
