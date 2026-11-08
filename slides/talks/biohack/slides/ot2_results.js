// One step: supplied MIC protocol scores before and after simulator-guided repair.
// TODO(final): Independently reproduce Jimmy's supplied simulator scores.
{
Deck.section(3);
Deck.slide('ot2-results', {
 before: 'evidence-verification',
 notes: `Source: benchmark/step3_MIC_benchmark/candidates_step3/benchmark_before_after.md and leaderboard.csv, supplied by Jimmy via Ramith on 2026-11-08. One initial sample per model, reasoning effort high; up to three repair rounds with simulator feedback. Weighted 16-row rubric normalized to 100. A failed gate scores zero; each repair subtracts five points from passing protocols. Gate checks analyzer errors, OT-2 robot type, and multichannel pipettes. GPT-OSS passes after repair but has serious liquid-handling errors; Nemotron still fails. Reference answer scores 100. The source describes API-level adjustments for simulation/scoring. Model labels are as supplied. These results have not been independently reproduced and are not wet-lab validation.`,
 mount(frame, {data, css, esc}) {
  const models = data.ot2Results.models;
  const before = models.filter(m => m.before_gate === 'pass').length;
  const after = models.filter(m => m.after_gate === 'pass').length;
  css(`.ot2-body{position:absolute;left:4.2%;right:4.2%;top:19%;font-size:var(--t-body)}.ot2-summary{margin:0 0 .8em;color:var(--accent);font-size:var(--t-lead)}.ot2-table{width:100%;border-collapse:collapse;font-size:var(--t-small)}.ot2-table th,.ot2-table td{text-align:right;padding:.38em .4em;border-bottom:1px solid var(--detail)}.ot2-table th:first-child,.ot2-table td:first-child{text-align:left;padding-left:0}.ot2-table th{color:var(--muted);font-weight:400}.ot2-table strong{color:var(--accent)}.ot2-rule{font-size:var(--t-caption);color:var(--muted);margin:.8em 0}.ot2-limit{font-size:var(--t-small);margin:.5em 0}.ot2-source{color:var(--accent)}`);
  frame.innerHTML = `<h2 class="deck-heading">OT-2 protocol benchmark: before and after repair</h2>
   <div class="ot2-body"><p class="ot2-summary">Simulator gate: ${before} / ${models.length} passed initially → ${after} / ${models.length} after repair</p>
   <table class="ot2-table"><thead><tr><th>Model</th><th>Before / 100</th><th>Repairs</th><th>After / 100</th><th>Final gate</th></tr></thead>
   <tbody>${models.map(m=>`<tr><td>${esc(m.name)}</td><td>${m.before.toFixed(1)}</td><td>${m.repairs}</td><td><strong>${m.after.toFixed(1)}</strong></td><td>${esc(m.after_gate)}</td></tr>`).join('')}</tbody></table>
   <p class="ot2-rule">One sample per model · up to 3 repairs · −5 points per repair · failed gate = 0</p>
   <p class="ot2-limit">Simulator success does not establish correct liquid handling or wet-lab success.</p></div>
   <p class="deck-caption">Jimmy’s supplied results · independent reproduction pending · <a class="ot2-source" href="https://github.com/sanjyotshenoy/what_we_test_next/blob/benchmark/jimmy-ot2/benchmark/step3_MIC_benchmark/candidates_step3/benchmark_before_after.md" target="_blank" rel="noopener">Source report ↗</a></p>`;
  return {enter(){}};
 }
});
Deck.section(null);
}
