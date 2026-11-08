/* Read-only replay of the sequential catalog in the original operator panel layout. */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api = async path => {const r=await fetch(path); if(!r.ok) throw new Error(`Saved results unavailable (${r.status}).`); return r.json();};
const details = (title, value) => `<details><summary>${esc(title)}</summary>${prettyValue(value)}</details>`;
let catalog, data, runs=[], generation=0, graph;
initializeVisuals();
function clearResult() {
  stopSimulation(); hideGraphTooltip();
  data=null; runs=[];
  for(const id of ['log','question','molecules','plate-svg','well-detail','downloads','robot-summary','feed','run-select']) $(id).replaceChildren();
  if(graph) {graph.destroy(); graph=null;}
  $('graph-detail').textContent='';
  setSimulation(null);
  $('robot-state').textContent='no run selected';
}
function question(snapshot) {
  const rr=snapshot.batches.flatMap(b=>b.manifest.runs||[]);
  const compounds=[...new Set(rr.map(r=>r.compound.replace(/\s*\(CHEMBL\d+\)/g,'')))];
  const species=[...new Set(rr.map(r=>r.species?.name).filter(Boolean))];
  return compounds.length>1 ? `Which inhibits ${species.join(' and ')} at a lower concentration: ${compounds.join(' or ')}?` : `What minimum concentration of ${compounds.join(' and ')} inhibits growth of ${species.join(' and ')}?`;
}
function drawRun() {
  const item=runs[Number($('run-select').value)]; if(!item) return;
  const {batch,run,snapshot}=item, plate=snapshot?.plate;
  const unit=plate?.unit||plate?.design?.unit||'';
  $('plate-svg').innerHTML='<span></span>'+Array.from({length:12},(_,i)=>`<span>${i+1}</span>`).join('');
  for(const row of 'ABCDEFGH') {
    $('plate-svg').insertAdjacentHTML('beforeend',`<span>${row}</span>`);
    for(let col=1;col<=12;col++) {
      const w=plate?.design?.wells?.find(w=>w.row===row&&w.column===col);
      const role=w?.role||'empty', kind=role.includes('growth')?'growth':role.includes('steril')?'sterility':role==='sample'?'sample':'';
      const surplus=(run.allocation?.surplus_rows||'').includes(row);
      const label=`${row}${col} · ${role} · ${w?.final_concentration??w?.final_uM??'—'} ${unit} · ${w?.volume_uL??'—'} µL${surplus?' · surplus technical well':''}`;
      const b=document.createElement('button'); b.className=`well ${kind}${surplus?' surplus':''}`;b.title=label;b.setAttribute('aria-label',label);b.textContent=kind==='growth'?'G':kind==='sterility'?'S':'';
      b.dataset.row=row; b.dataset.column=col; b.onclick=()=>{$('well-detail').textContent=label;};$('plate-svg').append(b);
    }
  }
  $('well-detail').textContent='Select a well · G: growth · S: sterility · dashed: surplus technical wells';
  const base=`/api/artifacts/${encodeURIComponent(data.session)}/${encodeURIComponent(batch.manifest.batch_id)}/${encodeURIComponent(run.run_id)}/`;
  $('downloads').innerHTML=[['protocol.py','OT-2 protocol'],['run_sheet.md','Run sheet'],['plate.json','Plate map'],['simulation.json','Simulator report']].map(([file,label])=>`<a href="${base+file}">${label}</a>`).join(' · ');
  const passed=run.simulation?.status==='passed'&&snapshot?.simulation?.status==='passed';
  $('robot-state').textContent=passed?'saved pass · hash verified':run.simulation?.status||'not run';
  $('robot-summary').textContent='Simulation only. No physical execution or measured MIC. The separate video does not execute this protocol.';
  setSimulation(passed ? snapshot.simulation : null);
}
async function selectSession() {
  const token=++generation, session=$('query').value; clearResult();
  if(!session) {$('status').textContent='No saved examples available for this model.';return;}
  $('status').textContent='Loading saved workflow…';
  try {
    const result=await api(`/api/planning?session=${encodeURIComponent(session)}`);
    if(token!==generation) return;
    if(!result.batches?.length) throw new Error('Saved artifacts are missing for this example.');
    data=result;$('question').textContent=question(data);
    $('status').textContent=`Precomputed · ${data.session}`;
    $('log').innerHTML=(data.evidence||[]).map(e=>details(e.tool,{inputs:e.args,result:e.result})).join('');
    for(const batch of data.batches) {
      for(const c of batch.batch?.compounds||[]) $('log').insertAdjacentHTML('beforeend',details(`Proposal · ${c.compound}`,c));
      $('log').insertAdjacentHTML('beforeend',details('Compiler checks and review requirements',{rules:batch.rules,review:batch.manifest.review}));
      for(const run of batch.manifest.runs||[]) runs.push({batch,run,snapshot:batch.runs.find(r=>r.run_id===run.run_id)});
    }
    $('run-select').innerHTML=runs.map(({run},i)=>`<option value="${i}">${esc(run.compound)} / ${esc(run.species?.name)} · ${esc(run.run_id)}</option>`).join('');
    drawGraph();drawMolecules();drawRun();
  } catch(e) {if(token===generation) {clearResult();$('status').textContent=e.message+' No live run was started.';}}
}
function selectModel() {
  const entries=catalog.examples.filter(e=>e.model===$('model').value);
  $('query').innerHTML=entries.map(e=>`<option value="${esc(e.session)}">${esc(e.question)}</option>`).join('');
  $('query').disabled=!entries.length;selectSession();
}
$('model').onchange=selectModel;$('query').onchange=selectSession;$('run-select').onchange=drawRun;
$('kg-fit').onclick=()=>graph?.fit(undefined,50);
$('kg-all').onclick=()=>drawGraph('all');
$('kg-focus').onclick=()=>drawGraph('focus');
(async()=>{try {
  catalog=await api('/api/precomputed');
  $('model').innerHTML=catalog.models.map(m=>`<option value="${esc(m.id)}">${esc(m.label)}</option>`).join('');
  $('model').disabled=false;selectModel();
} catch(e){$('status').textContent=e.message;}})();
(async()=>{try {
  const r=await api('/api/recording');
  if(r.available) {$('vid').src=r.url;$('vid').poster=r.poster;showSimulationTab(simulationTab);}
  $('video-note').textContent=r.available?'Separate 30-second physical recording; not execution of the selected protocol.':'The separate robot recording is unavailable.';
} catch(e){$('video-note').textContent='The separate robot recording is unavailable.';}})();
