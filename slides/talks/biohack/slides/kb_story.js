// Four construction/tool slides. Clicks progressively reveal sourced records and links.
{
Deck.section(2);
function story(id,title,rows,caption,notes){
 Deck.slide(id,{before:'evidence-graph',steps:3,notes,mount(frame,{css,esc}){
 css(`.ks-stage{position:absolute;left:4.2%;top:20%;width:91.6%;height:60%;pointer-events:none}.ks-stage canvas{position:absolute}.ks-labels{position:absolute;inset:0}.ks-node{position:absolute;width:27%;background:var(--bg);padding:.5em;text-align:center;font-size:var(--t-small);line-height:1.35}.ks-node strong{display:block;font-size:var(--t-body);color:var(--accent);margin-bottom:.5em}.ks-node small{display:block;font-size:var(--t-caption);color:var(--muted);margin-top:.6em}.ks-bottom{position:absolute;left:7%;right:7%;top:75%;font-size:var(--t-small);text-align:center}`);
 frame.innerHTML=`<h2 class="deck-heading">${esc(title)}</h2><div class="ks-stage"><div class="ks-labels">${rows.map((r,i)=>`<div class="ks-node reveal-in" data-from="${i+1}" style="left:${3.5+i*33}%;top:25%"><strong>${esc(r[0])}</strong>${esc(r[1])}<small>${esc(r[2])}</small></div>`).join('')}</div></div><p class="ks-bottom reveal-in" data-from="3">${esc(caption)}</p><p class="deck-caption">${esc(notes.split('\n')[0])}</p>`;
 const host=frame.querySelector('.ks-stage'),labels=host.querySelector('.ks-labels');
 const stage=Deck.manim(host,{scene:{frameHeight:5.9},build:({M,P})=>({nodes:[-5.3,0,5.3].map(x=>new M.Circle({radius:.28,color:P.accent,strokeWidth:2,fillOpacity:.04}).moveTo([x,2.05,0])),lines:[[-5,-.3],[.3,5]].map(([a,b])=>new M.Line({start:[a,2.05,0],end:[b,2.05,0],color:P.muted,strokeWidth:3}))}),steps:[({nodes},{M})=>[new M.Create(nodes[0])],({nodes,lines},{M})=>[new M.Create(lines[0]),new M.Create(nodes[1])],({nodes,lines},{M})=>[new M.Create(lines[1]),new M.Create(nodes[2])]]});
 host.append(labels);return{enter:(s,a)=>{Deck.show(frame,s,a);return stage.go(s,a);},freeze:stage.freeze,destroy:stage.dispose};
 }});
}
story('kb-biology-build','Building the biology knowledge base',[
 ['Published evidence','Paper metadata and reported assay activity','Example document: CHEMBL5356937'],
 ['ChEMBL records','Compound, target, assay, units and source IDs','Current importer reads ChEMBL 37 records'],
 ['Typed graph','Compound — INHIBITS — Target','14 nM lives on the edge, with assay and document references']
], 'Assay — FROM_DOC — Document preserves the source trail.',
 'Source: kg/biology graph CSVs and importer · kinase example\nThe current pipeline imports structured ChEMBL records. This is not a claim of automatic PDF-to-graph extraction. Example: CHEMBL4278808 to Q8TF76, assay CHEMBL5357346, document CHEMBL5356937. Assay/document references in the INHIBITS properties are not extra CSV edges.');
// TODO(final): domain-review the agent-curated protocol templates before claiming validation.
story('kb-protocol-build','Building the protocol knowledge base',[
 ['Source material','PubChem assay descriptions and NCATS guidance','MIC template also uses the team’s reference protocol'],
 ['Curated template','Reusable assay family with sourced defaults','Steps, readout, reagents, controls and parameter evidence'],
 ['Typed graph','Protocol — HAS_STEP — Step','NEXT orders steps; HAS_PARAM and HAS_RULE attach detail']
], 'Raw steps and parameter records can contain exact numbers and source quotes.',
 'Source: kg/protocols templates, rules and graph CSVs\nTemplates are agent-curated and require domain review. An LLM extractor exists; this slide does not claim demonstrated bulk automated paper extraction. Protocol graph contains 141 nodes and 367 edges in the exported snapshot.');
story('kb-bridge','Connecting biological evidence to a protocol',[
 ['Target identity','Haspin (Q8TF76)','MEMBER_OF identifies its target class'],
 ['Class hierarchy','Haspin family and broader kinase classes','SUBCLASS_OF supplies the ancestry'],
 ['Applicable assay','Kinase protocol family','APPLICABLE_TO links templates to supported classes']
], 'Biology suggests the activity scale; the protocol supplies assay structure and constraints.',
 'Source: agent/tools.py and both graph CSVs\nSchematic of real relation types, not a direct target-to-template edge. Agent template lookup walks the target class chain. Concentration anchoring is deterministic and is separate from an LLM’s design rationale.');
Deck.slide('kb-tools',{before:'evidence-graph',steps:3,notes:'Source: agent/tools.py TOOL_SPECS, agent/anchor.py and proposal flow. Four retrieval tools are exposed to the LLM. Initial lookup and numeric anchor are deterministic. The five-model pilot used fixed input packets and no retrieval tool loop.',mount(frame,{css}){
 css(`.kt-table{position:absolute;left:4.2%;top:20%;width:91.6%;border-collapse:collapse;font-size:var(--t-small)}.kt-table td{padding:.6em .5em;border-bottom:1px solid var(--detail)}.kt-table td:first-child{color:var(--accent);width:40%}.kt-note{position:absolute;top:69%;left:5%;right:5%;font-size:var(--t-small);line-height:1.5}`);
 frame.innerHTML=`<h2 class="deck-heading">Tools available to the proposal agent</h2><table class="kt-table"><tbody><tr class="reveal-in" data-from="1"><td>bio_kg_resolve</td><td>Resolve entities and target classes</td></tr><tr class="reveal-in" data-from="2"><td>bio_kg_analogs</td><td>Similar compounds measured on the same target</td></tr><tr class="reveal-in" data-from="2"><td>bio_kg_similar</td><td>Structural neighbors across targets</td></tr><tr class="reveal-in" data-from="3"><td>protocol_kg_templates</td><td>Applicable templates, steps and parameters</td></tr></tbody></table><p class="kt-note reveal-in" data-from="3"><strong>Algorithm:</strong> initial lookup, similarity ranking and numeric anchor.<br><strong>LLM:</strong> tool selection, assay choice and justified proposal.<br><strong>Pilot:</strong> fixed evidence packets; these retrieval tools were not invoked.</p><p class="deck-caption">Current agent capabilities are distinct from the three-case benchmark setup</p>`;
 return{enter:(s,a)=>Deck.show(frame,s,a)};
}});
Deck.section(null);
}
