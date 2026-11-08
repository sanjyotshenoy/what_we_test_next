// Four construction/tool slides. Clicks progressively reveal sourced records and links.
{
Deck.section(2);
Deck.slide('kb-tools',{before:'evidence-graph',steps:3,notes:'Source: agent/tools.py TOOL_SPECS, agent/anchor.py and proposal flow. Four retrieval tools are exposed to the LLM. Initial lookup and numeric anchor are deterministic. The five-model pilot used fixed input packets and no retrieval tool loop.',mount(frame,{css}){
 css(`.kt-table{position:absolute;left:4.2%;top:20%;width:91.6%;border-collapse:collapse;font-size:var(--t-small)}.kt-table td{padding:.6em .5em;border-bottom:1px solid var(--detail)}.kt-table td:first-child{color:var(--accent);width:40%}.kt-note{position:absolute;top:69%;left:5%;right:5%;font-size:var(--t-small);line-height:1.5}`);
 frame.innerHTML=`<h2 class="deck-heading">Tools available to the proposal agent</h2><table class="kt-table"><tbody><tr class="reveal-in" data-from="1"><td>bio_kg_resolve</td><td>Resolve entities and target classes</td></tr><tr class="reveal-in" data-from="2"><td>bio_kg_analogs</td><td>Similar compounds measured on the same target</td></tr><tr class="reveal-in" data-from="2"><td>bio_kg_similar</td><td>Structural neighbors across targets</td></tr><tr class="reveal-in" data-from="3"><td>protocol_kg_templates</td><td>Applicable templates, steps and parameters</td></tr></tbody></table><p class="kt-note reveal-in" data-from="3"><strong>Algorithm:</strong> initial lookup, similarity ranking and numeric anchor.<br><strong>LLM:</strong> tool selection, assay choice and justified proposal.<br><strong>Pilot:</strong> fixed evidence packets; these retrieval tools were not invoked.</p><p class="deck-caption">Current agent capabilities are distinct from the three-case benchmark setup</p>`;
 return{enter:(s,a)=>Deck.show(frame,s,a)};
}});
Deck.section(null);
}
