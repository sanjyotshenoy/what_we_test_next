// Recorded pilot results: headline totals, three-axis rubric, and observed limits/cost (one step each).
// Data is generated from committed benchmark results; no unmeasured baseline comparisons are displayed.
{
const notes='20 purposively selected cases: 15 biochemical, 5 cellular; five models, one response per case. 85 new completions plus 15 reused outputs with identical inputs/settings. All 100 freshly reviewed by isolated Astra-medium judges blinded to model identity under a frozen rubric. Four synthetic anchor checks do not establish expert calibration. Each axis 0–2, mean total 0–6. No measured retrieval lift, statistical superiority, MIC or wet-lab validation. Critical failures are reported separately. Source: benchmark/judge/RESULTS.md at c1a0e32. Generation used temperature 0 and low reasoning; judging used medium reasoning.';
for(const spec of [
 {name:'pilot-scores',heading:'Five models, twenty diagnostic cases',max:6,ticks:3,groups:d=>[{key:'total',label:['Mean rubric total','20 cases · maximum 6 per case'],values:Object.fromEntries(d.models.map(m=>[m.id,m.total]))}],foot:['Blinded Astra medium · provisional scores · one response per case','Fixed input packets · no measured retrieval lift or statistical ranking']},
 {name:'pilot-rubric',heading:'Where the rubric points come from',max:2,ticks:4,groups:d=>[{key:'suitability',label:['Right assay','and biological question']},{key:'steps',label:['Procedural','soundness']},{key:'numerical_soundness',label:['Numerical','soundness']}].map(g=>({...g,values:Object.fromEntries(d.models.map(m=>[m.id,m.axes[g.key]]))})),foot:['Mean score per axis: 0–2 · 20 cases per model · expert review pending','Partial credit includes unresolved settings · valid arithmetic is not biological validation']}
]){
 Deck.section(3);
 Deck.slide(spec.name,{before:'evidence-verification',notes,mount(frame,{data,esc}){
  const d=data.pilotResults;
  frame.innerHTML=`<h2 class="deck-heading">${esc(spec.heading)}</h2>`;
  const plot=Deck.groupedBars(frame,{max:spec.max,ticks:spec.ticks,format:v=>`${v}/${spec.max}`,series:d.models.map(m=>({key:m.id,label:m.name})),groups:spec.groups(d),footnote:spec.foot});
  return{enter:(step,animate)=>plot.show(step,animate)};
 }});
}
Deck.section(3);
Deck.slide('pilot-findings',{before:'evidence-verification',notes:notes+' New generation: 310831 receipted tokens, estimated $0.674688 plus $0.305636 allowance for three uncertain attempts. Astra token and billing receipts unavailable. Critical failure counts are cases with at least one judge flag, not validated failure rates.',mount(frame,{data,css,esc}){
 const d=data.pilotResults;
 css(`.pr-body{position:absolute;left:4.2%;right:4.2%;top:20%;display:grid;grid-template-columns:53% 42%;gap:5%;font-size:var(--t-body);line-height:1.3}.pr-body h3{font-size:var(--t-lead);color:var(--accent);margin:0 0 .5em}.pr-body p{margin:.5em 0 1em}.pr-body small{font-size:var(--t-small);color:var(--muted)}.pr-cost{width:100%;border-collapse:collapse;font-size:var(--t-small)}.pr-cost td{padding:.45em .2em;border-bottom:1px solid var(--detail)}.pr-cost td:last-child{text-align:right}.pr-link{color:var(--accent)}`);
 frame.innerHTML=`<h2 class="deck-heading">Useful designs still need evidence checks</h2><div class="pr-body"><div><h3>What the outputs revealed</h3><p><strong>Uncertainty matters.</strong> Kimi left the unsupported cellular series unresolved.</p><p><strong>Check internal consistency.</strong> DeepSeek specified both 11 and 10 points for one series.</p><p><strong>Require source support.</strong> GPT-OSS claimed pilot verification that was never supplied.</p><small>Draft grades need domain review. These cases do not measure MIC discovery or autonomous execution.</small></div><div><h3>Cases with critical failures</h3><table class="pr-cost"><tbody>${d.models.map(m=>`<tr><td>${esc(m.name)}</td><td>${m.critical_failures} / 20</td></tr>`).join('')}</tbody></table><p><small>New generation: ${d.new_generation_tokens.toLocaleString()} tokens<br>$${d.new_generation_estimate_usd.toFixed(3)} est. + $${d.unconfirmed_allowance_usd.toFixed(3)} reserved<br>Astra tokens / billing unavailable</small></p></div></div><p class="deck-caption"><a class="pr-link" href="../biohack/data/pilot_results.json" target="_blank" rel="noopener">Inspect chart data ↗</a> · <a class="pr-link" href="https://github.com/sanjyotshenoy/what_we_test_next/blob/c1a0e32/benchmark/judge/RESULTS.md" target="_blank" rel="noopener">Outputs, grading evidence and usage ledger ↗</a></p>`;
 return{enter(){}};
}});
Deck.section(null);
}
