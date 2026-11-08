/* Conceptual data flow reconstructed from saved artifacts, not an execution timeline. */
let workflowNodes=[], workflowTrigger=null;
const workflowIcons={
  model:'M4 5h16v14H4z M7 9l3 3-3 3 M12 15h5',
  context:'M5 4h14v16H5z M8 8h8 M8 12h8 M8 16h5',
  biology:'M12 5v5 M5 17l7-7 7 7 M9 3h6v4H9z M2 16h6v5H2z M16 16h6v5h-6z',
  literature:'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14 M15 15l6 6',
  proposal:'M4 20l4-1L20 7l-4-4L4 15z M13 6l4 4',
  checks:'M9 6h11 M9 12h11 M9 18h11 M3 6l1 1 2-3 M3 12l1 1 2-3 M3 18l1 1 2-3',
  protocols:'M8 6l-6 6 6 6 M16 6l6 6-6 6 M14 3l-4 18',
  simulation:'M5 4v16l15-8z'
};
function workflowMap(snapshot) {
  const evidence=snapshot.evidence||[], batches=snapshot.batches||[];
  const context=evidence.filter(e=>e.tool==='planning_context');
  const biology=evidence.filter(e=>e.tool==='biology_lookup');
  const literature=evidence.filter(e=>['literature_search','literature_read'].includes(e.tool));
  const proposals=batches.flatMap(b=>b.batch?.compounds||[]);
  const rules=batches.flatMap(b=>Object.values(b.rules||{}).flat()).filter(r=>r&&typeof r==='object');
  const reviews=rules.filter(r=>r.status==='needs_review').length;
  const failures=rules.filter(r=>!['passed','needs_review'].includes(r.status)).length;
  const records=batches.flatMap(batch=>(batch.manifest.runs||[]).map(run=>({batch,run,saved:batch.runs.find(r=>r.run_id===run.run_id)})));
  const verified=records.filter(({run,saved})=>run.simulation?.status==='passed'&&saved?.simulation?.status==='passed').length;
  const count=(n,one,many=one+'s')=>`${n} ${n===1?one:many}`;
  return [
    {id:'context',number:'01',title:'Protocol context',subtitle:count(context.length,'saved snapshot'),badge:context.length?'Saved':'Unavailable',tone:context.length?'':'muted',description:'The protocol template, lab capabilities and submission contract supplied to the planner.',evidence:context},
    {id:'biology',number:'02a',title:'Biological evidence',subtitle:count(biology.length,'graph lookup'),badge:biology.length?'Retrieved':'Unavailable',description:'Saved compound–organism lookups, including original measurements, units and source records.',evidence:biology},
    {id:'literature',number:'02b',title:'Literature evidence',subtitle:count(literature.filter(e=>e.tool==='literature_read').length,'passage read','passages read'),badge:literature.length?'Retrieved':'Unavailable',description:'Saved literature searches and the passages actually read by this agent. These are separate from graph evidence.',evidence:literature},
    {id:'proposal',number:'03',title:'Design experiments',subtitle:count(proposals.length,'compound proposal'),badge:proposals.length?'Proposed':'Unavailable',description:'The proposed experiments and field-level evidence links. Supplied assay settings remain synthetic inputs.',proposals},
    {id:'checks',number:'04',title:'Check the design',subtitle:count(rules.filter(r=>r.status==='passed').length,'rule passed','rules passed')+` · ${reviews} need review`,badge:failures?'Check results':reviews?'Review needed':rules.length?'Checked':'Unavailable',tone:failures?'bad':reviews?'review':'',description:'Software checks and remaining review requirements. Citation existence does not establish scientific applicability.',batches},
    {id:'protocols',number:'05',title:'Compile protocols',subtitle:count(records.length,'protocol record'),badge:records.length?'Generated':'Unavailable',description:'Separate OT-2 protocol records for each compound–species pair, with source identities and well allocations.',records},
    {id:'simulation',number:'06',title:'Simulate execution',subtitle:`${verified} / ${records.length} hash-verified passes`,badge:records.length&&verified===records.length?'Verified':'Incomplete',tone:records.length&&verified===records.length?'verified':'review',description:'Saved simulator results tied to the protocol hashes. These are software simulations, not physical execution or biological outcomes.',records}
  ];
}
function workflowNode(node) {
  return `<button type="button" class="workflow-node ${node.tone||''}" data-workflow-node="${node.id}" ${node.active?'aria-current="step"':''} aria-haspopup="dialog" aria-controls="workflow-dialog" aria-label="${esc(node.title)}: ${esc(node.subtitle)}. Open details."><span class="workflow-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="${workflowIcons[node.id]}"/></svg></span><span class="workflow-copy"><span class="workflow-kicker">${node.number} <span>${esc(node.badge)}</span></span><strong>${esc(node.title)}</strong><small>${esc(node.subtitle)}</small></span><span class="workflow-chevron" aria-hidden="true">↗</span></button>`;
}
function renderWorkflow(snapshot, live=null) {
  const previous=workflowNodes.length;
  if(!live) clearWorkflow();
  workflowNodes=workflowMap(snapshot);
  if(live) {
    workflowNodes.unshift({id:'model',number:'LLM',title:'Model output',subtitle:`Turn ${live.turn||0} / 16`,badge:'Waiting',description:'Visible model output streamed from the provider. Draft actions are not validated results; provider-returned reasoning is shown separately in the activity log.'});
    const active=['starting','running'].includes(live.state);
    for(const node of workflowNodes) {
      const step=live.steps?.[node.id];
      if(node.badge==='Unavailable'||node.id==='simulation'&&!node.records.length) {node.badge=active?'Queued':'Not reached';node.tone='pending';}
      if(step==='returned'&&['Queued','Not reached','Waiting'].includes(node.badge)) node.badge=node.id==='proposal'?'Draft ready':'Returned';
      if(step==='failed') {node.badge='Needs attention';node.tone='bad';}
      node.active=active&&(live.stage||'model')===node.id;
      if(node.active) {node.badge=node.id==='model'?'Generating':'Running';node.tone='running';}
      if(!active&&live.stage===node.id&&['failed','stopped'].includes(live.state)) {node.badge=live.state==='stopped'?'Stopped':'Failed';node.tone=live.state==='stopped'?'pending':'bad';}
    }
    if(previous&&$('log').querySelector('[data-workflow-node="model"]')) {
      for(const node of workflowNodes) {
        const button=$('log').querySelector(`[data-workflow-node="${node.id}"]`);
        button.className=`workflow-node ${node.tone||''}${button.classList.contains('selected')?' selected':''}`;
        button.querySelector('.workflow-kicker > span').textContent=node.badge;
        button.querySelector('.workflow-copy small').textContent=node.subtitle;
        button.setAttribute('aria-label',`${node.title}: ${node.badge}. ${node.subtitle}. Open details.`);
        if(node.active) button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');
      }
      return;
    }
  }
  const node=id=>workflowNode(workflowNodes.find(n=>n.id===id));
  const edge='<div class="workflow-edge" aria-hidden="true"><span></span></div>';
  const fork='<svg class="workflow-fork" viewBox="0 0 300 24" preserveAspectRatio="none" aria-hidden="true"><path d="M150 0V7Q150 12 145 12H80Q75 12 75 17V24 M150 7Q150 12 155 12H220Q225 12 225 17V24"/></svg>';
  $('log').innerHTML=`<div class="workflow-heading"><span>FROM EVIDENCE TO EXECUTION</span><small>Click a block to inspect</small></div><div class="workflow-map" aria-label="Saved scientific workflow">${live?node('model')+edge:''}${node('context')}${fork}<div class="workflow-branches">${node('biology')}${node('literature')}</div><div class="workflow-join">${fork}</div>${node('proposal')}${edge}${node('checks')}${edge}${node('protocols')}${edge}${node('simulation')}</div><p class="workflow-note">${live?'Live stages populate from returned artifacts. Highlighted blocks are currently running.':'Map of saved artifacts. Branches group evidence sources; they do not indicate parallel execution.'}</p>`;
}
function clearWorkflow() {
  const dialog=$('workflow-dialog');
  if(dialog.open) dialog.close();
  workflowNodes=[];workflowTrigger=null;
  $('workflow-detail-body').replaceChildren();$('log').replaceChildren();
}
function artifactLinks(record, files) {
  const base=`/api/artifacts/${encodeURIComponent(data.session)}/${encodeURIComponent(record.batch.manifest.batch_id)}/${encodeURIComponent(record.run.run_id)}/`;
  return `<nav class="workflow-downloads" aria-label="Saved artifacts">${files.map(([file,label])=>`<a href="${base+file}">${label}</a>`).join('')}</nav>`;
}
function showWorkflowDetails(id) {
  const node=workflowNodes.find(n=>n.id===id);if(!node) return;
  $('workflow-detail-title').textContent=node.title;
  $('workflow-detail-summary').textContent=node.description;
  $('workflow-detail-meta').textContent=`${node.subtitle} · ${data.session}`;
  let content='';
  if(id==='model') content='<pre id="workflow-model-output" class="live-text"></pre>';
  if(node.evidence) content=node.evidence.map((e,i)=>`<article class="workflow-record"><h3>${esc(e.tool.replaceAll('_',' '))} <span>${i+1}</span></h3>${e.retrieved_at?`<p class="muted">${esc(e.retrieved_at)}</p>`:''}${details('Tool inputs',e.args)}${details('Saved result',e.result)}</article>`).join('');
  if(node.proposals) content=node.proposals.map(c=>`<article class="workflow-record"><h3>${esc(c.compound)}</h3>${prettyValue(c.proposal)}${details('Parameter provenance',c.evidence_links)}</article>`).join('');
  if(node.batches) content=node.batches.map(b=>`<article class="workflow-record"><h3>Design review</h3>${prettyValue(b.rules)}${details('Review requirements',b.manifest.review)}</article>`).join('');
  if(node.records) content=node.records.map(r=>{
    const {run,saved}=r;
    const pass=run.simulation?.status==='passed'&&saved?.simulation?.status==='passed';
    const body=id==='simulation'?prettyValue({status:pass?'Passed · protocol hash verified':run.simulation?.status||'not run',commands:saved?.simulation?.commands,protocol_sha256:saved?.simulation?.protocol_sha256}):prettyValue({species:run.species,allocation:run.allocation,sources:saved?.sources,warnings:run.warnings});
    const files=id==='simulation'?[['simulation.json','Simulator report']]:[['protocol.py','OT-2 protocol'],['run_sheet.md','Run sheet'],['plate.json','Plate map']];
    return `<article class="workflow-record"><h3>${esc(run.run_id)} · ${esc(run.compound)}</h3><p class="muted">${esc(run.species?.name)}</p>${body}${artifactLinks(r,files)}</article>`;
  }).join('');
  if(!content&&typeof liveNodeRecords!=='undefined'&&liveNodeRecords[id]) {const event=liveNodeRecords[id];content=`<p>Live tool ${event.kind==='tool_start'?'input':'output'} preview. Draft inputs are not validated results.</p><pre class="live-text">${esc(event.text||event.message)}</pre>`;}
  $('workflow-detail-body').innerHTML=content||'<p>No saved records are available for this stage.</p>';
  if(id==='model') $('workflow-model-output').textContent=typeof liveModelText==='string'&&liveModelText||'Waiting for visible model output…';
  for(const button of $('log').querySelectorAll('[data-workflow-node]')) button.classList.toggle('selected',button.dataset.workflowNode===id);
  workflowTrigger=$('log').querySelector(`[data-workflow-node="${id}"]`);
  $('workflow-dialog').showModal();$('workflow-detail-body').scrollTop=0;
}
function initializeWorkflow() {
  $('log').addEventListener('click',e=>{const button=e.target.closest('[data-workflow-node]');if(button) showWorkflowDetails(button.dataset.workflowNode);});
  $('workflow-close').onclick=()=>$('workflow-dialog').close();
  $('workflow-dialog').addEventListener('close',()=>{if(workflowTrigger?.isConnected)workflowTrigger.focus({preventScroll:true});});
  $('workflow-dialog').addEventListener('click',e=>{const r=e.currentTarget.getBoundingClientRect();if(e.target===e.currentTarget&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)) e.currentTarget.close();});
}
