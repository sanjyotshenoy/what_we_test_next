/* Read-only visualizations. Live KG context is kept separate from retrieved evidence. */
function prettyValue(value, depth=0) {
  if(value===null||value===undefined) return '<span class="muted">Not supplied</span>';
  if(typeof value!=='object') return `<span>${esc(value)}</span>`;
  if(Array.isArray(value)) return value.length ? `<ul class="data-list">${value.map(v=>`<li>${prettyValue(v,depth+1)}</li>`).join('')}</ul>` : '<span class="muted">None</span>';
  return `<dl class="data-fields">${Object.entries(value).map(([k,v])=>`<div><dt>${esc(k.replaceAll('_',' '))}</dt><dd>${depth>2&&v&&typeof v==='object'?`<details><summary>View details</summary>${prettyValue(v,0)}</details>`:prettyValue(v,depth+1)}</dd></div>`).join('')}</dl>`;
}
let graphOverview, overviewRequest, graphRequest=0, tooltipPinned=false;
function hideGraphTooltip() {tooltipPinned=false;document.getElementById('graph-tooltip').hidden=true;}
function showGraphTooltip(event, pinned=false) {
  const element=event.target, tooltip=$('graph-tooltip');
  if(tooltipPinned&&!pinned) return;
  tooltipPinned=pinned;
  tooltip.innerHTML=`<button class="tooltip-close" aria-label="Close graph details">×</button><h3>${esc(element.data('label')||'Measurement')}</h3>${prettyValue(element.data('record'))}`;
  tooltip.querySelector('button').onclick=hideGraphTooltip;
  tooltip.hidden=false;
  const rect=$('cy').getBoundingClientRect(), point=event.renderedPosition||element.renderedPosition?.()||{x:20,y:20};
  const x=rect.left+point.x+14,y=rect.top+point.y+12;
  tooltip.style.left=`${Math.max(8,Math.min(x,innerWidth-tooltip.offsetWidth-8))}px`;
  tooltip.style.top=`${Math.max(8,Math.min(y,innerHeight-tooltip.offsetHeight-8))}px`;
}
document.addEventListener('keydown',e=>{if(e.key==='Escape') hideGraphTooltip();});
function retrievedGraph() {
  const nodes=new Map(),edges=[];
  for(const e of data?.evidence||[]) if(e.tool==='biology_lookup') {
    const r=e.result||{};
    for(const n of [...r.compound_matches||[],...r.species_matches||[]]) nodes.set(n.id,n);
    for(const m of r.measurements||[]) edges.push(m);
  }
  return {nodes:[...nodes.values()],edges};
}
async function drawGraph(mode='all') {
  const request=++graphRequest, session=data?.session;
  hideGraphTooltip();
  if(!session) return;
  $('graph-mode').textContent=mode==='all'?'KG overview':'retrieved subgraph';
  $('kg-all').setAttribute('aria-pressed',mode==='all');$('kg-focus').setAttribute('aria-pressed',mode==='focus');
  const retrieved=retrievedGraph(),ids=new Set(retrieved.nodes.map(n=>n.id));
  let source=retrieved;
  if(mode==='all') {
    try {
      if(!graphOverview) {
        overviewRequest ||= api('/api/graph/overview').catch(e=>{overviewRequest=null;throw e;});
        graphOverview=await overviewRequest;
      }
      source=graphOverview;
    } catch(e) {
      if(request===graphRequest&&data?.session===session) $('graph-detail').textContent='KG overview unavailable. Use Focus run for saved evidence.';
      return;
    }
  }
  if(request!==graphRequest||data?.session!==session) return;
  if(graph) graph.destroy();
  const known=new Set(source.nodes.map(n=>n.id));
  const nodes=source.nodes.map(n=>({data:{id:n.id,label:n.name,color:n.type==='Compound'?'#58a6ff':'#3fb950',record:n},classes:ids.has(n.id)?'relevant':''}));
  const edges=source.edges.filter(m=>known.has(m.src)&&known.has(m.dst)).map((m,i)=>({data:{id:`edge-${i}`,source:m.src,target:m.dst,
    label:mode==='all'?`${m.measurements} measurements`:`MIC ${m.props?.relation||''} ${m.props?.mic} ${m.props?.unit}`,record:m},classes:ids.has(m.src)&&ids.has(m.dst)?'relevant':''}));
  if(mode==='all') {
    const organisms=nodes.filter(n=>n.data.record.type==='Organism'),compounds=nodes.filter(n=>n.data.record.type==='Compound');
    for(const [group,radius] of [[organisms,350],[compounds,1100]]) group.forEach((n,i)=>{const a=2*Math.PI*i/group.length;n.position={x:radius*Math.cos(a),y:radius*Math.sin(a)};});
  }
  graph=cytoscape({container:$('cy'),elements:[...nodes,...edges],minZoom:.05,maxZoom:4,
    style:[
      {selector:'node',style:{width:mode==='all'?9:30,height:mode==='all'?9:30,'background-color':'data(color)',label:mode==='all'?'':'data(label)',color:'#e6edf3','font-size':12,'text-wrap':'wrap','text-max-width':140,'text-valign':'bottom','text-margin-y':5}},
      {selector:'edge',style:{width:mode==='all'?2.5:2,opacity:mode==='all'?.28:1,label:mode==='all'?'':'data(label)','curve-style':mode==='all'?'straight':'bezier','target-arrow-shape':mode==='all'?'none':'triangle',color:'#b7c4d6','font-size':10,'line-color':'#53657e','target-arrow-color':'#53657e'}},
      {selector:'node.relevant',style:{'border-width':3,'border-color':'#fff',width:30,height:30,label:'data(label)','font-size':mode==='all'?42:12}},
      {selector:'edge.relevant',style:{opacity:1,'line-color':'#58a6ff',width:mode==='all'?6:2}}
    ],layout:{name:mode==='all'?'preset':'circle',padding:45}});
  graph.on('mouseover','node, edge',e=>showGraphTooltip(e));
  graph.on('mouseout','node, edge',()=>{if(!tooltipPinned) $('graph-tooltip').hidden=true;});
  graph.on('tap','node, edge',e=>showGraphTooltip(e,true));
  graph.on('tap',e=>{if(e.target===graph) hideGraphTooltip();});
  graph.on('pan zoom',hideGraphTooltip);
  $('graph-detail').textContent=mode==='all'?`${source.nodes.length} compounds/organisms · ${source.counts.measurements.toLocaleString()} measurements grouped into ${source.edges.length.toLocaleString()} links. ${source.counts.types.Assay.toLocaleString()} assays and ${source.counts.types.Document.toLocaleString()} documents summarized on links. Highlighted: this run. Hover or tap for details; Focus run to zoom into saved evidence.`:'Saved retrieved measurements only. Hover a node or edge for details; tap to pin. Known MICs are background evidence, not new biological results.';
}
function drawMolecules() {
  const molecules=retrievedGraph().nodes.filter(n=>n.type==='Compound');
  $('molecules').innerHTML=molecules.map(n=>{
    const cached=['CHEMBL8','CHEMBL454950'].includes(n.id);
    return `<article><h3>${esc(n.name)}</h3>${cached?`<img class="molecule-image" src="/static/data/molecules/${n.id}.svg" alt="2D chemical structure of ${esc(n.name)}"><p class="muted">ChEMBL 2D structure · <a href="/static/data/molecules/${n.id}.mol" download>Download molfile</a></p>`:'<p>No cached structure depiction available.</p>'}<p>${esc(n.id)} · ${esc(n.source)} · <a href="/static/data/molecules/provenance.json">Structure sources</a></p>${details('Structure notation and provenance',{saved_smiles:n.props?.smiles,depiction:'ChEMBL 2D; not a measured 3D conformation'})}</article>`;
  }).join('');
  for(const img of $('molecules').querySelectorAll('img')) img.onerror=()=>{img.replaceWith(document.createTextNode('Structure image unavailable; saved notation remains below.'));};
}
let simulationSteps=[],simulationIndex=0,simulationTimer=null,simulationSlots=new Map(),simulationTab='simulation';
function stopSimulation() {clearInterval(simulationTimer);simulationTimer=null;document.getElementById('sim-play').textContent='Play';}
function locationInfo(text) {
  const match=String(text||'').match(/([A-H]\d+) of (.+?) on slot (\d+)/);
  return match?{well:match[1],labware:match[2],slot:Number(match[3])}:null;
}
function commandLocations(step) {
  const p=step?.payload||{};
  return [...new Set([p.location,p.source,p.dest,...(p.locations||[])].filter(Boolean))].map(locationInfo).filter(Boolean);
}
function setSimulation(report) {
  stopSimulation();simulationSteps=report?.runlog||[];simulationIndex=0;simulationSlots=new Map();
  for(const step of simulationSteps) for(const loc of commandLocations(step)) simulationSlots.set(loc.slot,loc.labware);
  $('feed').innerHTML=simulationSteps.map((s,i)=>`<li><button data-command="${i}">${esc(s.payload?.text||'Command')}</button></li>`).join('');
  for(const id of ['sim-play','sim-next','sim-reset','sim-seek']) $(id).disabled=!simulationSteps.length;
  $('sim-seek').max=Math.max(0,simulationSteps.length-1);
  renderSimulation();
}
function renderSimulation() {
  const step=simulationSteps[simulationIndex], p=step?.payload||{},locs=commandLocations(step),current=locs.at(-1);
  $('sim-seek').value=simulationIndex;$('sim-position').textContent=simulationSteps.length?`${simulationIndex+1} / ${simulationSteps.length}`:'No verified report';
  $('simulation-action').textContent=p.text||'No hash-verified simulator recording available for this protocol.';
  let svg='<svg viewBox="0 0 390 300" role="img" aria-label="OT-2 deck schematic for the selected simulator command">';
  for(let slot=1;slot<=12;slot++) {
    const x=12+((slot-1)%3)*126,y=12+(3-Math.floor((slot-1)/3))*69;
    const name=simulationSlots.get(slot)||'Unreferenced',active=locs.some(l=>l.slot===slot);
    const short=name.includes('Tip Rack')?'Tip rack':name.includes('Reservoir')?'Reservoir':name.includes('Plate')?'96-well plate':name.includes('Trash')?'Trash':name;
    svg+=`<g class="deck-slot${active?' active':''}"><rect x="${x}" y="${y}" width="116" height="58" rx="7"/><text x="${x+8}" y="${y+15}">Slot ${slot}</text><text x="${x+8}" y="${y+32}">${esc(short)}</text>${current?.slot===slot?`<circle cx="${x+94}" cy="${y+15}" r="6"/><text x="${x+8}" y="${y+48}">${esc(current.well)} · selected</text>`:''}</g>`;
  }
  $('simulation-stage').innerHTML=svg+'</svg><p class="caption">2D command playback · illustrative timing · highlighted locations from the saved simulator log.</p>';
  for(const well of $('plate-svg').querySelectorAll('.well')) {
    const match=locs.some(loc=>loc.labware.includes('Plate')&&Number(loc.well.slice(1))===Number(well.dataset.column)&&(/8.Channel/i.test(p.instrument||'')||loc.well[0]===well.dataset.row));
    well.classList.toggle('sim-active',match);
  }
  for(const [i,li] of [...$('feed').children].entries()) li.classList.toggle('now',i===simulationIndex);
  const li=$('feed').children[simulationIndex];
  if(li) $('feed').scrollTop=li.offsetTop-$('feed').offsetTop-30;
}
function showSimulationTab(tab) {
  simulationTab=tab;const sim=tab==='simulation';
  $('simulation-stage').hidden=!sim;$('simulation-action').hidden=!sim;$('vid').hidden=sim||!$('vid').getAttribute('src');$('video-note').hidden=sim;
  $('show-simulation').setAttribute('aria-pressed',sim);$('show-recording').setAttribute('aria-pressed',!sim);
  if(sim) $('vid').pause();else stopSimulation();
}
function initializeVisuals() {
$('sim-play').onclick=()=>{
  if(simulationTimer) return stopSimulation();
  if(simulationIndex>=simulationSteps.length-1) simulationIndex=0;
  $('sim-play').textContent='Pause';renderSimulation();
  simulationTimer=setInterval(()=>{if(simulationIndex>=simulationSteps.length-1) return stopSimulation();simulationIndex++;renderSimulation();},400);
};
$('sim-next').onclick=()=>{stopSimulation();simulationIndex=Math.min(simulationIndex+1,simulationSteps.length-1);renderSimulation();};
$('sim-reset').onclick=()=>{stopSimulation();simulationIndex=0;renderSimulation();};
$('sim-seek').oninput=()=>{stopSimulation();simulationIndex=Number($('sim-seek').value);renderSimulation();};
$('feed').onclick=e=>{const b=e.target.closest('[data-command]');if(b){stopSimulation();simulationIndex=Number(b.dataset.command);renderSimulation();}};
$('show-simulation').onclick=()=>showSimulationTab('simulation');$('show-recording').onclick=()=>showSimulationTab('recording');
showSimulationTab('simulation');
}
