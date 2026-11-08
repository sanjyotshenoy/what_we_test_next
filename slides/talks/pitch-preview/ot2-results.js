// Two steps: initial protocol scores, then scores after simulator-guided repair.
// TODO(final): Independently reproduce Jimmy's supplied simulator scores.
{
Deck.slide('pitch-ot2-results', {before:'pitch-demo', steps:2,
 notes:'Separate OT-2 MIC protocol benchmark supplied by Jimmy on 2026-11-08; not an end-to-end execution of the preceding kinase/cell proposals. Five models, one initial sample each, high reasoning effort. Same MIC prompt; 16 weighted rubric rows normalized to 100. A failed simulator/hardware gate scores zero. Up to three repairs using simulator feedback, with five points deducted per repair. Gate pass count rises from one to four, but correct liquid handling is not guaranteed: GPT-OSS passes after three repairs while its dilution/control logic is wrong. Nemotron still fails after three repairs. Repair counts in chart order: 0, 1, 2, 3, 3. Reference scores 100. Model labels and scores are as supplied; independent reproduction is pending. Source: benchmark/step3_MIC_benchmark/candidates_step3/benchmark_before_after.md and leaderboard.csv. Source documents simulator API-level adjustments. This small benchmark does not establish statistical superiority or wet-lab success.',
 mount(frame,{data,css}) {
  const d=data.ot2Results;
  const passes=key=>d.models.filter(m=>m[key]==='pass').length;
  const labels=[['Kimi','K3.1 Pro'],['DeepSeek','V4.1 Flash 1017'],['GLM 5.3'],['GPT-OSS','120B'],['Nemotron','3 Super']];
  css(`.po-summary{position:absolute;left:7%;right:7%;top:16%;font-size:var(--t-body);color:var(--accent);margin:0}.po-plot .deck-plot-key{top:27%;font-size:var(--t-small)}.po-plot .deck-plot-chart{left:12%;right:7%;top:39%;height:29%}.po-plot .deck-plot-group{gap:calc(1.5 * var(--u))}.po-plot .deck-plot-bar{width:calc(3.2 * var(--u))}.po-plot .deck-plot-val{font-size:var(--t-small)}.po-plot .deck-plot-label{font-size:var(--t-caption);top:calc(100% + 1.5 * var(--u))}.po-rule{position:absolute;left:7%;right:7%;top:81%;font-size:var(--t-caption);color:var(--muted);margin:0}.po-caption{font-size:var(--t-caption)}.po-caption a{color:var(--accent)}`);
  frame.innerHTML=`<h2 class="deck-heading">Can the model write a runnable OT-2 protocol?</h2><p class="po-summary"></p><p class="po-rule">Score / 100 · one sample per model · up to 3 repairs · −5 points per repair · failed gate = 0</p><p class="deck-caption po-caption">Jimmy’s supplied results · simulation ≠ wet-lab validation · <a href="../biohack/data/ot2_results.json" target="_blank" rel="noopener">Data ↗</a></p>`;
  const plot=Deck.groupedBars(frame,{max:100,ticks:4,format:v=>String(v),strong:'after',series:[{key:'before',label:'Initial answer',step:1},{key:'after',label:'After repair (penalty included)',step:2}],groups:d.models.map((m,i)=>({key:m.name,label:labels[i],values:{before:m.before,after:m.after}})),footnote:[]});
  plot.root.classList.add('po-plot');
  return {enter(step,animate){
   frame.querySelector('.po-summary').textContent=step===1?`Simulator gate: ${passes('before_gate')} / 5 passed on the first attempt`:`Simulator gate: ${passes('before_gate')} / 5 initially → ${passes('after_gate')} / 5 after repair; liquid-handling errors remain`;
   plot.show(step,animate);
  }};
 }
});
}
