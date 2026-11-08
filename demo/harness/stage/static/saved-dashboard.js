/* Read-only replay of the sequential catalog in the original operator panel layout. */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api = async path => {const r=await fetch(path); if(!r.ok) throw Object.assign(new Error(`Results unavailable (${r.status}).`),{status:r.status}); return r.json();};
const details = (title, value) => `<details><summary>${esc(title)}</summary>${prettyValue(value)}</details>`;
let catalog, data, runs=[], generation=0, graph, liveQuestion='';
const liveSession=new URLSearchParams(location.search).get('run');
initializeDashboardHeader();
initializeDashboardTheme();
initializeVisuals();
initializeDashboardLayout();
initializeWorkflow();
function clearResult() {
  stopSimulation(); hideGraphTooltip(); clearWorkflow();
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
    if(!result.batches?.length && !liveSession) throw new Error('Saved artifacts are missing for this example.');
    data=result;$('question').textContent=liveSession?liveQuestion:question(data);
    $('status').textContent=`${liveSession?'Your run':'Precomputed'} · ${data.session}${!data.batches.length?' · No compiled protocol yet; return to live planning for progress.':''}`;
    renderWorkflow(data);
    for(const batch of data.batches) {
      for(const run of batch.manifest.runs||[]) runs.push({batch,run,snapshot:batch.runs.find(r=>r.run_id===run.run_id)});
    }
    $('run-select').innerHTML=runs.map(({run},i)=>`<option value="${i}">${esc(run.compound)} / ${esc(run.species?.name)} · ${esc(run.run_id)}</option>`).join('');
    drawGraph();drawMolecules();drawRun();
  } catch(e) {if(token===generation) {clearResult();$('status').textContent=e.message+' No live run was started.';}}
}
function selectModel(preferred) {
  const entries=catalog.examples.filter(e=>e.model===$('model').value);
  $('query').innerHTML=entries.map(e=>`<option value="${esc(e.session)}">${esc(e.question)}</option>`).join('');
  if(typeof preferred==='string'&&entries.some(e=>e.session===preferred)) $('query').value=preferred;
  $('query').disabled=!entries.length;selectSession();
}
$('model').onchange=selectModel;$('query').onchange=selectSession;$('run-select').onchange=drawRun;
$('kg-fit').onclick=()=>graph?.fit(undefined,50);
$('kg-all').onclick=()=>drawGraph('all');
$('kg-focus').onclick=()=>drawGraph('focus');
let liveCursor=0, liveModelText='', liveTimer=null, liveSnapshotKey='', liveTextBlock=null;
const liveNodeRecords={};
let liveRefresh=0, liveJobState='starting', liveOutputChunks=0, liveOutputCharacters=0;
function appendLiveEvents(job) {
  const container=$('live-output-events'), scroller=$('live-output');
  const follow=scroller.scrollHeight-scroller.scrollTop-scroller.clientHeight<90;
  if(job.events_truncated) $('live-feed-note').textContent='Earlier activity expired from the bounded feed. Artifact details remain available.';
  for(const event of job.events||[]) {
    if(event.id<=liveCursor) continue;
    liveCursor=event.id;
    if(['tool_start','tool_result'].includes(event.kind)&&event.stage) {
      liveNodeRecords[event.stage]=event;
      if(event.tool==='planning_submit'&&event.kind==='tool_start') liveNodeRecords.proposal=event;
    }
    if(event.kind==='model_delta') {
      if(!liveTextBlock) addRecord('Generated model output');
      liveTextBlock.append(document.createTextNode(event.text||''));
      liveModelText=(liveModelText+(event.text||'')).slice(-200000);
      liveOutputChunks++;liveOutputCharacters+=(event.text||'').length;
      $('live-receipt').textContent=`${liveOutputChunks} output chunks · ${liveOutputCharacters.toLocaleString()} characters received · last output at run +${event.elapsed??0}s`;
      continue;
    }
    liveTextBlock=null;
    if(event.kind==='model_start') {liveModelText='';addRecord(`Model turn ${event.turn} · visible output`);}
    else if(event.kind==='model_end') continue;
    else {
      addRecord(`${event.elapsed??0}s · ${event.message}`);
      if(event.text) liveTextBlock.textContent=event.text+(event.truncated?'\n[Preview truncated; inspect workflow artifacts for the full record.]':'');
      liveTextBlock=null;
    }
  }
  $('live-preview-text').textContent=liveModelText.slice(-1600)||'Waiting for the model’s visible output…';
  $('live-preview-text').scrollTop=$('live-preview-text').scrollHeight;
  while(container.children.length>100) container.firstElementChild.remove();
  const modelView=$('workflow-model-output');
  if(modelView) {
    const body=$('workflow-detail-body'),atEnd=body.scrollHeight-body.scrollTop-body.clientHeight<90;
    modelView.textContent=liveModelText||'Waiting for visible model output…';
    if(atEnd) body.scrollTop=body.scrollHeight;
  }
  if(follow) scroller.scrollTop=scroller.scrollHeight;
  function addRecord(title) {
    const article=document.createElement('article'),heading=document.createElement('h3');
    heading.textContent=title;liveTextBlock=document.createElement('pre');liveTextBlock.className='live-text';
    article.append(heading,liveTextBlock);container.append(article);
  }
}
async function updateLiveArtifacts(snapshot, job) {
  const signature=JSON.stringify(snapshot);
  if(signature!==liveSnapshotKey) {
    const previousEvidence=JSON.stringify(data?.evidence||[]);
    const previous=runs[Number($('run-select').value)];
    const key=item=>item?`${item.batch.manifest.batch_id}/${item.run.run_id}`:'';
    const runSignature=item=>JSON.stringify(item?{run:item.run,snapshot:item.snapshot}:null);
    const priorRun=runSignature(previous);
    data=snapshot;liveSnapshotKey=signature;
    runs=data.batches.flatMap(batch=>(batch.manifest.runs||[]).map(run=>({batch,run,snapshot:batch.runs.find(r=>r.run_id===run.run_id)})));
    $('run-select').innerHTML=runs.map(({run},i)=>`<option value="${i}">${esc(run.compound)} / ${esc(run.species?.name)} · ${esc(run.run_id)}</option>`).join('');
    const selected=Math.max(0,runs.findIndex(item=>key(item)===key(previous)));$('run-select').value=String(selected);
    if(runSignature(runs[selected])!==priorRun) drawRun();
    if(!graph) await drawGraph();
    else if(previousEvidence!==JSON.stringify(data.evidence)) {
      if($('kg-focus').getAttribute('aria-pressed')==='true') {
        const zoom=graph.zoom(),pan=graph.pan();await drawGraph('focus');graph?.zoom(zoom);graph?.pan(pan);
      } else {
        const ids=new Set(retrievedGraph().nodes.map(n=>n.id));
        graph.nodes().forEach(n=>n.toggleClass('relevant',ids.has(n.id())));
        graph.edges().forEach(e=>e.toggleClass('relevant',ids.has(e.data('source'))&&ids.has(e.data('target'))));
      }
    }
    if(!$('structure').classList.contains('selected-molecule')) drawMolecules();
  }
  renderWorkflow(data,job);
}
async function pollLive() {
  const refresh=++liveRefresh;
  try {
    let [job,snapshot]=await Promise.all([api(`/api/runs/${encodeURIComponent(liveSession)}?after=${liveCursor}`),api(`/api/planning?session=${encodeURIComponent(liveSession)}`)]);
    if(!['starting','running'].includes(job.state)) snapshot=await api(`/api/planning?session=${encodeURIComponent(liveSession)}`);
    if(refresh!==liveRefresh) return;
    appendLiveEvents(job);await updateLiveArtifacts(snapshot,job);
    if(refresh!==liveRefresh) return;
    updateLiveState(job);$('status').textContent=`${job.message} · ${job.session}`;
    const active=['starting','running'].includes(job.state);
    $('live-stop').disabled=!active;
    if(active) liveTimer=setTimeout(pollLive,1000);
  } catch(e) {
    if(refresh!==liveRefresh) return;
    if(e.status===404) {updateLiveState({state:'expired'});renderWorkflow(data,{state:'expired'});$('status').textContent='This private run has expired or is unavailable to this browser.';$('live-stop').disabled=true;return;}
    $('live-connection').textContent='Disconnected · reconnecting…';
    $('status').textContent=`Live updates interrupted: ${e.message} Retrying…`;
    liveTimer=setTimeout(pollLive,5000);
  }
}
function updateLiveState(job) {
  liveJobState=job.state;
  const active=['starting','running'].includes(job.state);
  $('run-tag').textContent=job.state;
  $('live-connection').textContent=active?`Live · turn ${job.turn||0} · connected`:`Run ${job.state}`;
  $('source-tag').textContent=active?'Live run':`Live run · ${job.state}`;
  $('live-stop').disabled=!active;
  $('live-stop').textContent=active?'Interrupt run':`Run ${job.state}`;
}
async function interruptLive() {
  ++liveRefresh;clearTimeout(liveTimer);
  $('live-stop').disabled=true;$('live-stop').textContent='Interrupting…';
  $('status').textContent='Interrupting the model and active tools…';
  const response=await fetch(`/api/runs/${encodeURIComponent(liveSession)}/stop`,{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Run':'1'},body:'{}'});
  if(!response.ok) throw new Error(`Interrupt unavailable (${response.status}). The run may still be active.`);
  const job=await response.json();
  updateLiveState(job);renderWorkflow(data,job);$('status').textContent=job.message;
  return job;
}
function interruptFailed(error) {
  $('status').textContent=error.message;$('live-stop').disabled=false;$('live-stop').textContent='Interrupt run';
  liveTimer=setTimeout(pollLive,1000);
}
async function loadTraceSwitcher() {
  const menu=$('trace-switch');menu.hidden=false;
  try {
    const choices=await api('/api/precomputed');
    for(const entry of choices.examples) {
      const option=document.createElement('option');option.value=entry.session;
      option.textContent=`${choices.models.find(m=>m.id===entry.model)?.label||entry.model} · ${entry.question}`;
      menu.append(option);
    }
    menu.disabled=!choices.examples.length;
    menu.onchange=async()=>{
      const selected=menu.value;if(!selected) return;
      menu.disabled=true;
      try {
        if(['starting','running'].includes(liveJobState)) await interruptLive();
        location.assign(`/?trace=${encodeURIComponent(selected)}`);
      } catch(e) {menu.value='';menu.disabled=false;interruptFailed(e);}
    };
  } catch(e) {menu.options[0].textContent='Precomputed traces unavailable';}
}
function setupLive() {
  $('live-toolbar').hidden=false;$('live-preview').hidden=false;$('live-stop').hidden=false;
  for(const [id,output] of [['live-workflow-tab',false],['live-output-tab',true]]) $(id).onclick=()=>{
    $('log').hidden=output;$('live-output').hidden=!output;$('live-preview').hidden=output;
    $('live-workflow-tab').setAttribute('aria-pressed',String(!output));$('live-output-tab').setAttribute('aria-pressed',String(output));
  };
  $('live-expand').onclick=()=>$('live-output-tab').click();
  $('live-stop').onclick=async()=>{
    try {await interruptLive();await pollLive();} catch(e) {interruptFailed(e);}
  };
  loadTraceSwitcher();
  addEventListener('pagehide',()=>clearTimeout(liveTimer),{once:true});
}

(async()=>{try {
  if(liveSession) {
    data={session:liveSession,evidence:[],batches:[]};setupLive();
    const job=await api(`/api/runs/${encodeURIComponent(liveSession)}`);
    liveQuestion=job.question;
    $('source-tag').textContent='Your run';$('run-tag').textContent=job.state;
    $('source-note').textContent='New run with your supplied key. Proposed and simulated results are not biological measurements. Stages and artifacts update automatically while this run progresses.';
    $('model').innerHTML=`<option>${esc(job.model)}</option>`;
    $('query').innerHTML=`<option value="${esc(liveSession)}">${esc(job.question.split('\n')[0])}</option>`;
    document.querySelector('a[href="/planner"]').href=`/planner?run=${encodeURIComponent(liveSession)}`;
    data={session:liveSession,evidence:[],batches:[]};
    $('question').textContent=liveQuestion.split('\n')[0].replace(/^Scientist question: /,'');
    $('live-inputs').hidden=false;$('live-input-text').textContent=liveQuestion;
    renderWorkflow(data,job);updateLiveState(job);
    await pollLive();return;
  }
  catalog=await api('/api/precomputed');
  $('model').innerHTML=catalog.models.map(m=>`<option value="${esc(m.id)}">${esc(m.label)}</option>`).join('');
  const requestedTrace=new URLSearchParams(location.search).get('trace');
  const selected=catalog.examples.find(e=>e.session===requestedTrace);
  if(selected) $('model').value=selected.model;
  $('model').disabled=false;selectModel(selected?.session);
} catch(e){if(liveSession&&e.status===404) {updateLiveState({state:'expired'});renderWorkflow(data,{state:'expired'});$('live-preview-text').textContent='This run expired or is unavailable. Choose a precomputed trace to continue.';}$('status').textContent=e.message;}})();
(async()=>{try {
  const r=await api('/api/recording');
  if(r.available) {$('vid').src=r.url;$('vid').poster=r.poster;showSimulationTab(simulationTab);}
  $('video-note').textContent=r.available?'Separate 30-second physical recording; not execution of the selected protocol.':'The separate robot recording is unavailable.';
} catch(e){$('video-note').textContent='The separate robot recording is unavailable.';}})();
