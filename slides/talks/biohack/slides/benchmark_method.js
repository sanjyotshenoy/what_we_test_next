// Benchmark story: 1 inspect source evidence; 2 conceal query-pair/source records.
// Reviewer toggle replays the manim masking animation without exposing answers to a model.
{
Deck.section(3);
const points={compound:[-5,2.6],measurement:[0,2.6],target:[5,2.6],assays:[0,0],documents:[0,-2.7],examples:[-5,-1.5],classes:[5,0],template:[5,-2.7]};
const labels={compound:['Query compound','CHEMBL4278808'],measurement:['Pair measurements','14 nM reference'],target:['Haspin target','Q8TF76'],assays:['6 associated assays','all excluded'],documents:['2 supporting documents','all excluded'],examples:['Other compounds','retained evidence'],classes:['Target class','retained'],template:['Protocol family','parameterized cards']};
const hiddenKeys=['measurement','assays','documents'];
Deck.slide('benchmark-mask',{
 before:'pilot-scores',steps:2,interactive:true,
 notes:'Schematic for actual case 1. INHIBITS is an edge in the real KG, drawn here as a measurement card for teaching; source nodes are grouped, not a literal complete neighborhood. The split excludes both query-pair measurements, their two documents (CHEMBL4261587 and CHEMBL5356937), six assays and all affected edges: 24 total. The reference shown is 14 nM from CHEMBL5357346, document CHEMBL5356937. Retained protocol cards are manually generalized; exact template numbers/quotes are not passed to the model. The actual run uses isolated input JSON, not the full remaining graph. Each case is filtered independently. Reveal toggle is a reviewer affordance, not access control. Data: graph/cases/case-1.review.json and benchmark/runs/*/manifest.json. Cross-database duplicate-source audit is still incomplete.',
 mount(frame,{css,esc}){
  css(`.bm-stage{position:absolute;left:4.2%;top:23%;width:59%;height:57%;pointer-events:none}.bm-label{position:absolute;transform:translate(-50%,-50%);text-align:center;font-size:var(--t-caption);line-height:1.2;background:var(--bg);padding:.3em;border-radius:.3em;min-width:7em;transition:opacity .35s}.bm-label strong{display:block}.bm-label small{font-size:var(--t-micro);color:var(--muted)}.bm-label.held{color:var(--plot-5)}.bm-masked .bm-label.held{opacity:0}.bm-side{position:absolute;left:67%;right:4.2%;top:24%;font-size:var(--t-caption);line-height:1.35}.bm-side h3{font-size:var(--t-body);color:var(--accent);margin:0 0 .5em}.bm-side p{margin:.7em 0}.bm-switch{position:absolute;left:4.2%;top:16%;z-index:5}.bm-labels{position:absolute;inset:0;pointer-events:none}.bm-stage canvas{position:absolute}.bm-status{color:var(--plot-5);font-weight:bold}.bm-caution{font-size:var(--t-caption);color:var(--muted)}`);
  frame.innerHTML=`<h2 class="deck-heading">Build the case by concealing the answer</h2><button class="deck-switch bm-switch" aria-pressed="true"><i></i><span>Answer visible · conceal it</span></button><div class="bm-stage"><div class="bm-labels">${Object.entries(points).map(([k,[x,y]])=>`<div class="bm-label ${hiddenKeys.includes(k)?'held':''}" style="left:${50+x/16*100}%;top:${50-y/9*100}%"><strong>${esc(labels[k][0])}</strong><small>${esc(labels[k][1])}</small></div>`).join('')}</div></div><div class="bm-side"><h3>Case 1 · haspin inhibition</h3><p class="bm-status">Source evidence visible</p><p><strong>Exclude:</strong> both measurements, 2 documents, 6 assays and affected edges.</p><p><strong>Model receives:</strong> the question, 7 generalized step cards, 5 retained measurements and guidelines.</p><p class="bm-caution">Step-specific numbers → parameter slots.</p></div><p class="deck-caption">Case 1 schematic · 24 edges excluded · reviewer toggle; isolated JSON for the model</p>`;
  const host=frame.querySelector('.bm-stage');
  const stage=Deck.manim(host,{
   build:({M,P})=>{
    const nodes=Object.fromEntries(Object.entries(points).map(([k,[x,y]])=>[k,new M.Circle({radius:.32,color:hiddenKeys.includes(k)?P.series[4]:P.accent,fillOpacity:.18,strokeWidth:3}).moveTo([x,y,0])]));
    const joins=[['compound','measurement'],['measurement','target'],['measurement','assays'],['assays','documents'],['examples','target'],['target','classes'],['template','classes']];
    const lines=joins.map(([a,b])=>new M.Line({start:[...points[a],0],end:[...points[b],0],color:hiddenKeys.includes(a)||hiddenKeys.includes(b)?P.series[4]:P.muted,strokeWidth:2}));
    return{nodes,lines};
   },
   steps:[({nodes,lines},{M})=>[...lines.map(l=>new M.Create(l,{duration:.65})),...Object.values(nodes).map(n=>new M.FadeIn(n,{duration:.65}))],({nodes,lines},{M})=>[...hiddenKeys.map(k=>new M.FadeOut(nodes[k],{duration:.65})),...lines.slice(0,4).map(l=>new M.FadeOut(l,{duration:.65}))]]
  });
  // Keep HTML labels above manim's canvas and toggle them with the same scene state.
  host.append(frame.querySelector('.bm-labels'));
  let visible=true;
  function show(step,animate){visible=step===1;frame.classList.toggle('bm-masked',!visible);const b=frame.querySelector('.bm-switch');b.setAttribute('aria-pressed',String(visible));b.querySelector('span').textContent=visible?'Answer visible · conceal it':'Answer concealed · reveal it';frame.querySelector('.bm-status').textContent=visible?'Source evidence visible':'Query evidence concealed';return stage.go(step,animate);}
  frame.querySelector('.bm-switch').onclick=e=>{e.stopPropagation();show(visible?2:1,true);};
  return{enter:(step,animate)=>show(step,animate),freeze:stage.freeze,destroy:stage.dispose};
 }
});
Deck.slide('benchmark-grade',{
 before:'pilot-scores',steps:3,
 notes:'The evaluated model sees only the input packet and returns assay/system/readout, ordered step-card instructions, numeric parameters or null, controls, rationale, citations and limitations. Codex reviews final outputs against the draft rubric after generation; answers are not included in model requests. Each axis is 0–2 per case. Three cases × three axes × two points = 18 possible points/model. Scores are provisional, unblinded and uncalibrated; no expert validation or separate paid judge. Numerical coverage against held-out IC50 is an offline diagnostic, conditional on assay comparability, not proof of protocol validity. Missing values and unsupported claims remain explicit; no post-generation repair was scored.',
 mount(frame,{css}){
  css(`.bg-flow{position:absolute;left:4.2%;right:4.2%;top:18%;display:flex;justify-content:space-between;align-items:center;font-size:var(--t-small);padding:.6em 0;border-bottom:1px solid var(--detail)}.bg-flow strong{color:var(--accent)}.bg-grid{position:absolute;left:4.2%;right:4.2%;top:32%;display:grid;grid-template-columns:repeat(3,1fr);gap:3%}.bg-card{padding:1em .8em;border:1px solid var(--detail);border-radius:.4em;font-size:var(--t-small);line-height:1.35}.bg-card h3{margin:0 0 .5em;font-size:var(--t-body);color:var(--accent)}.bg-card p{margin:.5em 0}.bg-card small{font-size:var(--t-small);color:var(--muted)}.bg-total{position:absolute;left:4.2%;right:4.2%;top:76%;font-size:var(--t-small);line-height:1.4}`);
  frame.innerHTML=`<h2 class="deck-heading">Then grade the proposal on three axes</h2><div class="bg-flow"><span><strong>Model input</strong><br>Filtered packet only</span><span>→</span><span><strong>Model output</strong><br>Assay + steps + parameters + citations</span><span>→</span><span><strong>Reviewer context</strong><br>Output + held-out evidence + rubric</span></div><div class="bg-grid"><div class="bg-card reveal-in" data-from="1"><h3>1 · Right experiment</h3><p>Does this assay answer the biological question?</p><small>Viability ≠ direct BTK inhibition.</small></div><div class="bg-card reveal-in" data-from="2"><h3>2 · Sound steps</h3><p>Are stages, controls and analysis complete and ordered?</p><small>Accept supported alternatives; flag invented details.</small></div><div class="bg-card reveal-in" data-from="3"><h3>3 · Sound numbers</h3><p>Are values justified and consistent? Is uncertainty explicit?</p><small>Check arithmetic; report reference coverage separately.</small></div></div><div class="bg-total"><strong>0 = unsuitable / invalid · 1 = partial · 2 = supported and coherent</strong><br>3 cases × 3 axes × 2 = <strong>18 points per model</strong>. Report failures and abstentions too.</div><p class="deck-caption">Provisional Codex review · grading after generation · no paid judge or expert calibration</p>`;
  return{enter:(step,animate)=>Deck.show(frame,step,animate)};
 }
});
Deck.section(null);
}
