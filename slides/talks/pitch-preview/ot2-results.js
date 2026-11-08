// Two steps: no-plan scores, then scores when an experiment plan is supplied.
// TODO(final): Independently reproduce Jimmy's supplied simulator scores.
{
Deck.slide('pitch-ot2-results', {before:'pitch-demo', steps:2,
 notes:'Source: data/jimmy-plan-comparison.png, supplied by Ramith on 2026-11-08 at 18:27 UTC. Comparison is no plan (step 3 only) versus with plan (step 2 + 3), not initial answer versus repair. Five samples per model per condition; discard the two lowest and average the remaining three. Scores out of 100. Values transcribed exactly from the screenshot; underlying run-level results were not supplied. Four models improve and Nemotron remains at zero. GLM rises 55.3 to 73.0 (+17.7 points). The supplied all-model values are 40.1 and 46.7; the displayed with-plan model scores average 46.06, so the reported aggregate needs reconciliation. Do not interpret the supplied aggregate as an independently recalculated mean or claim statistical significance. Separate simulation benchmark, not wet-lab validation or an end-to-end execution of the kinase/cell proposals.',
 mount(frame,{data,css}) {
  const d=data.ot2PlanResults;
  css(`.po-summary{position:absolute;left:7%;right:7%;top:16%;font-size:var(--t-body);color:var(--accent);margin:0}.po-plot .deck-plot-key{top:27%;font-size:var(--t-small)}.po-plot .deck-plot-chart{left:12%;right:7%;top:39%;height:29%}.po-plot .deck-plot-group{gap:calc(1.5 * var(--u))}.po-plot .deck-plot-bar{width:calc(2.6 * var(--u))}.po-plot .deck-plot-val{font-size:var(--t-caption)}.po-plot .deck-plot-label{font-size:var(--t-caption);top:calc(100% + 1.5 * var(--u))}.po-rule{position:absolute;left:7%;right:7%;top:81%;font-size:var(--t-caption);color:var(--muted);margin:0}.po-caption{font-size:var(--t-caption)}.po-caption a{color:var(--accent)}`);
  frame.innerHTML=`<h2 class="deck-heading">Does an experiment plan improve OT-2 protocols?</h2><p class="po-summary"></p><p class="po-rule">Score / 100 · 5 samples each · lowest 2 dropped · remaining 3 averaged</p>`;
  const plot=Deck.groupedBars(frame,{max:100,ticks:5,format:v=>Number.isInteger(v)?String(v):v.toFixed(1),strong:'with_plan',series:[{key:'no_plan',label:'No plan',step:1},{key:'with_plan',label:'With Plan',step:2}],groups:d.models.map(m=>({key:m.name,label:m.label,values:{no_plan:m.no_plan,with_plan:m.with_plan}})),footnote:[]});
  plot.root.classList.add('po-plot');
  return {enter(step,animate){
   frame.querySelector('.po-summary').textContent=step===1?'OT-2 MIC benchmark · protocol generation without an experiment plan':'With a plan: four model scores increase; GLM gains 17.7 points';
   plot.show(step,animate);
  }};
 }
});
}
