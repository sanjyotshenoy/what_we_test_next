const $ = id => document.getElementById(id)
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
let current = null, batchID = null, runID = null, saved = '', lastSnapshot = '', lastActivity = '', polling = false
const api = async (path, body) => {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  if (!response.ok) throw Error((await response.text()).slice(0,500))
  return response.json()
}
const health = await api('/api/health')
const viewer = health.read_only === true
if (!health.session && health.default_session) saved = health.default_session
if (viewer) {
  saved = health.default_session
  document.querySelector('.composer').hidden = true
  $('keys').hidden = true; $('model').closest('label').hidden = true
  document.querySelector('footer a').hidden = true
  $('connection').textContent = 'Prepared results · view only'
  $('activity-description').textContent = 'Prepared results selected by the operator.'
  $('activity').textContent = 'Inspect published evidence and simulation artifacts. Running new experiments requires operator access.'
}
// Fixed physical recording is independent of agent state, selection, and simulation.
try {
  const recording = await api('/api/recording')
  if (recording.available) {
    const video = $('robot-video')
    video.src = recording.url; video.poster = recording.poster
    $('recording-caption').textContent = `${recording.duration_seconds.toFixed(0)} seconds · ${recording.speed_multiplier.toFixed(1)}× speed · silent playback`
    video.onerror = () => { $('recording-error').hidden = false }
    $('recording-card').hidden = false
  }
} catch { /* Recording availability must not block evidence or simulation views. */ }
const alert = message => { $('alert').textContent = message; $('alert').hidden = !message }
const guard = fn => async (...args) => { try { await fn(...args) } catch (e) { alert(e.message) } }
let agentBusy = false
const setBusy = busy => {
  agentBusy = Boolean(busy)
  for (const id of ['submit','model','keys']) $(id).disabled = viewer || busy
}
setBusy(health.agent_status && health.agent_status !== 'idle')
const badge = (text, status) => `<span class="badge ${['failed','error','rejected','stale','timeout'].includes(status)?'error':status==='passed'||status==='simulated'?'':'neutral'}">${esc(text)}</span>`
function evidence(records) {
  const count = records.filter(r => r.tool !== 'literature_search').length
  $('evidence-count').textContent = `${count} sources`
  $('evidence').innerHTML = records.map(r => {
    const x = r.result || {}
    if (r.tool === 'biology_lookup') return `<article class="source"><span class="badge neutral">Bacterial KG</span><h3>${esc(x.resolution)} · ${esc(x.total_measurements)} measurements</h3><code>${esc(x.evidence_id)}</code><details><summary>Raw MICs, identity and limitations</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details></article>`
    if (r.tool === 'planning_context') return `<article class="source"><span class="badge neutral">Team protocol</span><h3>Broth microdilution MIC</h3><code>${esc(x.evidence_id)}</code><p class="small">${esc(x.template?.curation)}</p><p class="small warning-text">${esc(x.template?.todo)}</p><details><summary>Source notes & limits</summary><pre>${esc(JSON.stringify({notes:x.template?.notes,limits:x.limits},null,2))}</pre></details></article>`
    if (r.tool === 'literature_search') return `<article class="source"><span class="badge neutral">Discovery · not yet evidence</span><h3>${esc(r.args?.query)}</h3>${(x.papers||[]).map(p=>`<p class="small">${esc(p.title)}<br><code>${esc(p.document_id)}</code></p>`).join('')}</article>`
    const meta=x.metadata||{}, doi=String(meta.doi||'').replace(/^https?:\/\/(dx\.)?doi.org\//,'')
    return `<article class="source"><span class="badge">Read source passage</span><h3>${esc(meta.title||'Source paper')}</h3><code>${esc(x.evidence_id)}</code>${doi?`<p><a target="_blank" rel="noopener" href="https://doi.org/${encodeURIComponent(doi)}">Paper DOI ↗</a></p>`:''}<details><summary>Lines ${esc(x.start)}–${esc(x.end)} · exact passage</summary><pre>${esc(x.passage)}</pre></details></article>`
  }).join('') || '<p class="empty">Sources appear as the agent retrieves them.</p>'
}
function download(batch, file, label) {
  const href = `/api/artifacts/${encodeURIComponent(current.session)}/${encodeURIComponent(batch)}/${file.split('/').map(encodeURIComponent).join('/')}`
  return `<a href="${href}" download>${esc(label)}</a>`
}
function renderDesign() {
  const batches=current?.batches||[]
  let selected=batches.find(b=>b.manifest.batch_id===batchID)||batches.at(-1)
  if (!selected) {
    $('batch-status').outerHTML='<span id="batch-status" class="badge neutral">Awaiting design</span>'
    $('batch-picker').innerHTML=''; $('design').innerHTML='<p class="empty">Validated compound × species runs will appear here.</p>'
    $('review').innerHTML='<p class="empty">Rule checks, source assumptions, and resource needs will appear after submission.</p>'; return
  }
  const m=selected.manifest; batchID=m.batch_id
  $('batch-status').outerHTML=`<span id="batch-status" class="badge ${m.status==='simulated'?'':'warning'}">${esc(m.status.replaceAll('_',' '))}</span>`
  $('batch-picker').innerHTML=batches.length>1?`<label>Batch <select id="batch-select">${batches.map(b=>`<option value="${esc(b.manifest.batch_id)}" ${b.manifest.batch_id===batchID?'selected':''}>${esc(b.manifest.batch_id)} · ${esc(b.manifest.status)}</option>`).join('')}</select></label>`:''
  $('batch-select')?.addEventListener('change',e=>{batchID=e.target.value;runID=null;renderDesign()})
  const runs=m.runs||[], run=runs.find(r=>r.run_id===runID)||runs[0]; runID=run?.run_id
  const detail=selected.runs.find(r=>r.run_id===runID)||{}, plate=detail.plate, report=detail.simulation
  const pass=runs.filter(r=>r.simulation?.status==='passed').length
  const compoundCount=new Set(runs.map(r=>r.compound)).size, speciesCount=new Set(runs.map(r=>r.species.name)).size
  const rationales=[...new Set((selected.batch?.compounds||[]).map(c=>c.proposal?.rationale).filter(Boolean))]
  $('design').innerHTML=`<div class="facts"><div class="fact"><b>${compoundCount} × ${speciesCount}</b><span>compounds × species</span></div><div class="fact"><b>${runs.length}</b><span>separate sequential runs</span></div><div class="fact"><b>${pass}/${runs.length}</b><span>simulations passed</span></div></div>
  ${rationales.map(r=>`<p class="small warning-text">${esc(r)}</p>`).join('')}
  <label>Inspect run <select id="run-select" class="run-select">${runs.map(r=>`<option value="${esc(r.run_id)}" ${r.run_id===runID?'selected':''}>${esc(r.run_id)} · ${esc(r.compound)} × ${esc(r.species.name)} · ${esc(r.simulation.status)}</option>`).join('')}</select></label>
  <div class="source-map">${Object.entries(detail.sources||{}).map(([well,s])=>`<span><b>${esc(well)}</b> · ${esc(s.identity||s.role)}</span>`).join('')}</div>
  <div id="plate" class="plate" aria-label="96-well plate map"></div><div class="legend"><span><i></i>Sample</span><span><i class="growth"></i>Growth control</span><span><i class="sterility"></i>Sterility control</span><span>Dashed = surplus technical wells</span></div>
  <p class="small">Requested rows: ${esc(run?.allocation?.requested_rows)}. Surplus rows: ${esc(run?.allocation?.surplus_rows||'none')}. Surplus wells are not counted as requested replicates.</p>
  <div id="well-detail" class="well-detail">Select a well to inspect its planned final concentration and volume.</div>
  <p>${badge(run?.simulation?.status,run?.simulation?.status)} <span class="small">${report?`${report.commands} simulated commands · protocol hash verified`:'No verified simulator report for this protocol.'}</span></p>
  ${run?.simulation?.error?`<p class="warning-text">${esc(run.simulation.error)}</p>`:''}
  <details><summary>Simulator command log</summary><pre>${esc(report?report.runlog.map(s=>s.payload?.text||'').join('\n'):'No verified log available.')}</pre></details>
  <div class="downloads">${download(batchID,`${runID}/protocol.py`,'OT-2 protocol')}${download(batchID,`${runID}/plate.json`,'Plate map')}${download(batchID,`${runID}/run_sheet.md`,'Run sheet')}${report?download(batchID,`${runID}/simulation.json`,'Simulation report'):''}</div>`
  $('run-select').onchange=e=>{runID=e.target.value;renderDesign()}
  if (plate?.design?.wells) {
    const grid=$('plate'); grid.innerHTML='<span></span>'+Array.from({length:12},(_,i)=>`<span class="axis">${i+1}</span>`).join('')
    for (const row of 'ABCDEFGH') {
      grid.insertAdjacentHTML('beforeend',`<span class="axis">${row}</span>`)
      for (let column=1;column<=12;column++) {
        const w=plate.design.wells.find(w=>w.row===row&&w.column===column)
        const button=document.createElement('button'), role=w?.role||'empty'
        const concentration=w?.final_concentration??w?.final_uM, unit=plate.unit||plate.design.unit
        const surplus=run.allocation.surplus_rows.includes(row)
        button.type='button'; button.className=`well ${role.includes('growth')?'growth':role.includes('steril')?'sterility':''} ${surplus?'surplus':''}`
        const text=`${row}${column} · ${role} · ${concentration??'—'} ${unit} final · ${w?.volume_uL??'—'} µL · ${surplus?'surplus technical well':'requested row'}`
        button.title=text; button.setAttribute('aria-label',text); button.textContent=role==='sample'?Number(concentration).toPrecision(2):role.includes('growth')?'G':'S'
        if (role==='sample') button.style.backgroundColor=`hsl(158 40% ${16+20*(12-column)/12}%)`
        button.onclick=()=>$('well-detail').textContent=text; grid.append(button)
      }
    }
  }
  const warnings=[...new Set([...(m.review||[]),...runs.flatMap(r=>r.warnings||[])])]
  $('review').innerHTML=`<div class="review-grid"><div><h3>Review before any lab execution</h3><ul>${warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul><p class="small">${esc(m.execution)}</p></div><div><h3>Resources & provenance</h3><p class="small">${m.resources?.plates_total??runs.length} plates · ${m.resources?.fresh_tip_rack_loads??'—'} fresh tip-rack loads · ${m.resources?.listed_tip_racks??'—'} tip racks listed in lab configuration.</p><p class="small warning-text">${esc(m.resources?.note)}</p><p class="small">Team commit: <code>${esc(m.team_commit)}</code></p><details><summary>Protocol KG rule checks</summary><pre>${esc(JSON.stringify(selected.rules,null,2))}</pre></details><details><summary>Submitted proposal & field citations</summary><pre>${esc(JSON.stringify(selected.batch,null,2))}</pre></details><div class="downloads">${download(batchID,'proposals.jsonl','Proposals JSONL')}${download(batchID,'evidence.json','Evidence snapshot')}${download(batchID,'manifest.json','Manifest')}${Object.keys(selected.rules||{}).length?download(batchID,'rules.json','Rule report'):''}</div></div></div>`
}
function render(data) {
  current=data; $('session').textContent=data.session||'No session yet'
  $('view-label').textContent=saved?'Saved artifacts · not a live run':'Live session'
  $('view-label').className=`badge ${saved?'warning':''}`
  evidence(data.evidence||[]); renderDesign()
  const latest=data.batches.at(-1)?.manifest
  for (const [id,done] of [['context',data.evidence.some(r=>r.tool==='planning_context')],['evidence',data.evidence.some(r=>r.tool==='literature_read')],['design',!!latest],['simulation',latest?.status==='simulated']]) $('step-'+id).classList.toggle('done',!!done)
}
function renderActivity(data) {
  $('cost').textContent=data.cost?`$${data.cost.toFixed(4)}`:''
  $('activity').innerHTML=data.items.map(i=>i.type==='tool'?`<div class="activity-item tool ${['error','rejected','failed'].includes(i.outcome)||i.status==='error'?'error':''}"><strong>${esc(i.name)}</strong>${esc(i.status)}${i.outcome?' · '+esc(i.outcome):''}${i.details?'<pre>'+esc(typeof i.details==='string'?i.details:JSON.stringify(i.details,null,2))+'</pre>':''}</div>`:`<div class="activity-item ${i.type==='error'?'error':''}">${esc(i.text)}</div>`).join('')||'<p class="empty">Ready for a question.</p>'
}
async function refresh() {
  if (polling) return; polling=true
  try {
    const data=await api('/api/planning'+(saved?'?session='+encodeURIComponent(saved):'')), serialized=JSON.stringify(data)
    if (serialized!==lastSnapshot) {lastSnapshot=serialized;render(data)}
    if (!saved) {
      const activity=await api('/api/activity'), text=JSON.stringify(activity)
      if(text!==lastActivity){lastActivity=text;renderActivity(activity)}
      if (!agentBusy && activity.items.length) {
        const outcomes=activity.items.filter(i=>i.type==='tool').map(i=>i.outcome)
        $('run-state').textContent=outcomes.includes('simulated')?'Simulation complete':outcomes.includes('compiled')?'Compiled · not simulated':'Stopped before compilation'
      }
    }
  } catch(e) {alert(e.message)} finally {polling=false}
}
async function loadSessions() {
  const sessions=await api('/api/planning/sessions')
  $('saved').innerHTML=(viewer?'':'<option value="">Current live session</option>')+sessions.map(s=>`<option value="${esc(s.session)}">${esc(s.session)} · ${s.run_count} runs · saved</option>`).join('')
  $('saved').value=saved
}
$('saved').onchange=guard(async e=>{
  saved=e.target.value; batchID=null;runID=null;lastSnapshot='';lastActivity='';alert('')
  if(saved){$('activity').innerHTML='<p class="empty">Viewing saved artifacts. These may come from an agent or direct backend tests; this view does not certify autonomous completion.</p>';$('cost').textContent=''}
  await refresh()
})
$('prompt-form').onsubmit=guard(async e=>{
  e.preventDefault(); const text=$('prompt').value.trim(); if(!text)return
  alert('');setBusy(true)
  try {await api('/api/prompt',{text});saved='';$('saved').value='';lastSnapshot='';$('run-state').textContent='Agent running';await refresh()}
  catch(e){setBusy(false);throw e}
})
$('stop').onclick=guard(async()=>{await api('/api/abort',{});$('run-state').textContent='Stopped';await refresh()})
$('new').onclick=guard(async()=>{await api('/api/new',{});saved='';batchID=null;runID=null;lastSnapshot='';lastActivity='';alert('');$('run-state').textContent='Ready';await loadSessions();await refresh()})
$('example').onclick=guard(async()=>{const r=await fetch('/static/data/rehearsal.txt');if(!r.ok)throw Error('Rehearsal prompt unavailable');$('prompt').value=await r.text()})
$('graph-example').onclick=guard(async()=>{const r=await fetch('/static/data/graph-rehearsal.txt');if(!r.ok)throw Error('Graph rehearsal prompt unavailable');$('prompt').value=await r.text()})
$('model').onchange=guard(async e=>{const [providerID,...rest]=e.target.value.split('/');await api('/api/model',{providerID,modelID:rest.join('/')})})
$('keys').onclick=guard(async()=>{const d=await api('/api/keys');$('key-profile').innerHTML=d.profiles.map(n=>`<option ${n===d.active?'selected':''}>${esc(n)}</option>`).join('');$('key-dialog').showModal()})
$('key-close').onclick=()=>$('key-dialog').close()
$('key-form').onsubmit=async e=>{
  e.preventDefault();$('key-error').textContent=''
  try {await api('/api/keys',{name:$('key-name').value||$('key-profile').value,key:$('key-value').value,save:true});$('key-value').value='';$('key-dialog').close();lastSnapshot='';lastActivity='';await refresh()}
  catch(e){$('key-error').textContent=e.message}
}
if (!viewer) {
const events=new EventSource('/api/stream')
events.onmessage=e=>{
  const data=JSON.parse(e.data)
  if(data.replay){$('connection').textContent='Recorded replay';$('connection').className='badge warning';for(const id of ['submit','stop','new','keys','model','prompt'])$(id).disabled=true;return}
  if(data.type==='hello'||data.type==='status'){$('connection').textContent=data.opencode?'OpenCode connected':'OpenCode offline';$('connection').className='badge '+(data.opencode?'':'error')}
  if(data.type==='oc'){
    const ev=data.event,pr=ev.properties||{}
    if(ev.type==='session.status'){setBusy(pr.status?.type!=='idle');$('run-state').textContent=pr.status?.type==='idle'?'Agent finished':`Agent ${pr.status?.type||'working'}`}
    if(ev.type==='session.error'){setBusy(false);$('run-state').textContent='Agent error';alert(pr.error?.data?.message||'Agent error; inspect activity')}
    if(ev.type==='session.idle'){setBusy(false);loadSessions().catch(e=>alert(e.message));refresh()}
  }
  if(data.type==='reset'){lastSnapshot='';lastActivity='';refresh()}
}
events.onerror=()=>{$('connection').textContent='Reconnecting';$('connection').className='badge warning'}
}
await guard(async()=>{
  const data=await api('/api/models')
  $('model').innerHTML=data.models.map(m=>`<option value="${esc(m.providerID+'/'+m.modelID)}" ${m.providerID===data.current.providerID&&m.modelID===data.current.modelID?'selected':''}>${esc(m.name)}</option>`).join('')
})()
await guard(loadSessions)();await refresh();setInterval(refresh,2000)
