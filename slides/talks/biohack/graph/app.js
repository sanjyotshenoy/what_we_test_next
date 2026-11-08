/* Explore real CSV records. Hidden edges are session-local thought experiments. */
'use strict';
const $ = id => document.getElementById(id);
const {nodes, edges} = window.GRAPH_DATA;
const byId = new Map(nodes.map(n => [n.id, n]));
const adjacency = new Map();
edges.forEach((e,i) => { e.index=i; for(const id of new Set([e.src,e.dst])) {if(!adjacency.has(id)) adjacency.set(id,[]); adjacency.get(id).push(e);}});
const colors=['#268197','#a16cbd','#cf9135','#608a46','#bf6377','#6b7fc4'];
const types=[...new Set(nodes.map(n=>n.type))].sort();
const color=type=>colors[types.indexOf(type)%colors.length];
let selected=byId.has('P10721')?'P10721':nodes[0].id;
let hidden=new Set(), scale=1, tx=0, ty=0;
const name=id=>byId.get(id)?.name || id;
function button(text, action, parent){const b=document.createElement('button');b.textContent=text;b.onclick=action;parent.append(b);return b;}
function inspect(record){$('details').replaceChildren();const pre=document.createElement('pre');pre.textContent=JSON.stringify(record,null,2);$('details').append(pre);if(record.index!==undefined)button('Hide this edge in this view',()=>{hidden.add(record.index);render();inspect(record);},$('details'));}
function search(){const query=$('search').value.toLowerCase();const found=nodes.filter(n=>`${n.name} ${n.id} ${n.type}`.toLowerCase().includes(query));$('results').replaceChildren();found.slice(0,30).forEach(n=>button(`${n.name} · ${n.type} (${n.id})`,()=>{selected=n.id;render();inspect(n);},$('results')));const p=document.createElement('p');p.className='note';p.textContent=`${found.length.toLocaleString()} matches; showing first ${Math.min(30,found.length)}.`;$('results').append(p);}
for(const rel of [...new Set(edges.map(e=>e.rel))].sort()){const o=document.createElement('option');o.value=o.textContent=rel;$('relation').append(o);}
function svg(tag,attrs){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);return el;}
function transform(){$('scene').setAttribute('transform',`translate(${tx} ${ty}) scale(${scale})`);}
function render(){const ids=new Set([selected]);let frontier=[selected],capped=false;const relation=$('relation').value;
for(let hop=0;hop<Number($('depth').value);hop++){const next=[];for(const id of frontier){for(const e of adjacency.get(id)||[]){if(hidden.has(e.index)||(relation&&e.rel!==relation))continue;const other=e.src===id?e.dst:e.src;if(!byId.has(other)||ids.has(other))continue;if(ids.size>=65){capped=true;continue;}ids.add(other);next.push(other);}}frontier=next;}
const visible=edges.filter(e=>!hidden.has(e.index)&&(!relation||e.rel===relation)&&ids.has(e.src)&&ids.has(e.dst));
$('focus').textContent=`${name(selected)} · ${selected}`;$('status').textContent=`${ids.size} nodes · ${visible.length} edges · ${hidden.size} hidden${capped?' · Neighborhood capped at 65 nodes; filter relationships to explore further.':''}`;
const positions=new Map([[selected,{x:500,y:360}]]);const others=[...ids].filter(id=>id!==selected);others.forEach((id,i)=>{const a=2*Math.PI*i/others.length;const r=others.length>25?(i%2?285:190):250;positions.set(id,{x:500+Math.cos(a)*r*1.35,y:360+Math.sin(a)*r});});
const scene=$('scene');scene.replaceChildren();$('edge-list').replaceChildren();
for(const e of visible){const a=positions.get(e.src),b=positions.get(e.dst);const line=svg('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'#afbdcd','stroke-width':1.5,'marker-end':'url(#arrow)',class:'edge'});const title=svg('title',{});title.textContent=`${name(e.src)} → ${e.rel} → ${name(e.dst)}`;line.append(title);line.onclick=()=>inspect(e);scene.append(line);button(`${name(e.src)} → ${e.rel} → ${name(e.dst)}`,()=>inspect(e),$('edge-list'));}
for(const id of ids){const n=byId.get(id),p=positions.get(id);const group=svg('g',{class:'node',tabindex:0,role:'button','aria-label':`${n.name}, ${n.type}`,transform:`translate(${p.x} ${p.y})`});group.append(svg('circle',{r:id===selected?16:10,fill:color(n.type),stroke:'#fff','stroke-width':2}));const label=svg('text',{y:27,'text-anchor':'middle'});label.textContent=n.name.length>24?n.name.slice(0,22)+'…':n.name;group.append(label);const title=svg('title',{});title.textContent=`${n.name} (${id}) · ${n.type}`;group.append(title);const choose=()=>{selected=id;render();inspect(n);};group.onclick=choose;group.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};scene.append(group);}
$('legend').replaceChildren();for(const type of new Set([...ids].map(id=>byId.get(id).type))){const span=document.createElement('span');span.style.borderColor=color(type);span.textContent=type;$('legend').append(span);}transform();}
$('search').oninput=search;$('relation').onchange=render;$('depth').onchange=render;$('reset').onclick=()=>{hidden.clear();render();inspect(byId.get(selected));};$('plus').onclick=()=>{scale=Math.min(4,scale*1.2);transform();};$('minus').onclick=()=>{scale=Math.max(.3,scale/1.2);transform();};$('fit').onclick=()=>{scale=1;tx=ty=0;transform();};
let drag=null;const graph=$('graph');graph.onpointerdown=e=>{if(e.target.closest('.node,.edge'))return;const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(graph.getScreenCTM().inverse());drag={x:p.x,y:p.y,tx,ty};graph.setPointerCapture(e.pointerId);};graph.onpointermove=e=>{if(!drag)return;const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(graph.getScreenCTM().inverse());tx=drag.tx+p.x-drag.x;ty=drag.ty+p.y-drag.y;transform();};graph.onpointerup=graph.onpointercancel=()=>{drag=null;};
$('totals').textContent=`Snapshot: ${nodes.length.toLocaleString()} nodes / ${edges.length.toLocaleString()} edges. Biology + protocols joined by shared IDs. ${edges.filter(e=>!byId.has(e.src)||!byId.has(e.dst)).length} edges reference missing nodes and cannot be drawn.`;search();render();inspect(byId.get(selected));
