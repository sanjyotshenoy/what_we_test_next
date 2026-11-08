// TODO(final): conceptual bacterial workflow, not a recorded end-to-end run; no measured values are invented.
{
Deck.hide('grounded-design');
Deck.slide('evidence-proposal', {
 steps:4,
 notes:'Conceptual bacterial workflow. Related compounds have measured activity on the organism of interest. Papers support those measurements; protocol templates are a separate source of assay structure, controls and defaults, not necessarily the original protocols from those papers. Together they inform a reviewable experiment proposal for compound X and the supplied panel. Species-level evidence does not establish a result for every strain. Current agent retrieval is IC50-based; the bacterial graph and downstream MIC execution exist separately. No end-to-end bacterial run or measured inhibition is claimed. Proposal fields shown here are categories, not populated experimental recommendations.',
 mount(frame,{css}) {
 css(`
 .ep-diagram{position:absolute;inset:18% 4.2% 15%;}
 .ep-lines{position:absolute;width:100%;height:100%;overflow:visible;}
 .ep-edge{fill:none;stroke:var(--accent);stroke-width:2;}
 .ep-flow{fill:none;stroke:var(--muted);stroke-width:2;}
 .ep-node{position:absolute;width:5.6%;aspect-ratio:1;border:2px solid var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--t-body);background:var(--bg);color:var(--accent);transform:translate(-50%,-50%);}
 .ep-strain{width:8%;aspect-ratio:1.35;border-radius:45%;color:var(--plot-2);border-color:var(--plot-2);}
 .ep-label{position:absolute;font-size:var(--t-small);color:var(--muted);text-align:center;line-height:1.3;}
 .ep-label strong{color:var(--fg);font-weight:600;}
 .ep-stack{position:absolute;width:16%;height:29%;color:var(--muted);}
 .ep-paper{position:absolute;inset:0;border:2px solid currentColor;background:var(--bg);border-radius:calc(.35 * var(--u));}
 .ep-paper:nth-child(1){transform:translate(8%,-12%);opacity:.4;}
 .ep-paper:nth-child(2){transform:translate(4%,-6%);opacity:.7;}
 .ep-paper:nth-child(3){padding:12%;box-sizing:border-box;}
 .ep-paper i{display:block;border-top:2px solid currentColor;margin:13% 0;width:85%;opacity:.4;}
 .ep-paper i:last-child{width:55%;}
 .ep-stack-label{position:absolute;top:110%;width:125%;left:-12.5%;text-align:center;font-size:var(--t-small);color:var(--fg);}
 .ep-proposal{position:absolute;left:72%;top:14%;width:27%;height:75%;border:2px solid var(--accent);border-radius:calc(.5 * var(--u));background:var(--bg);padding:2% 2.5%;box-sizing:border-box;}
 .ep-proposal h3{font-size:var(--t-lead);color:var(--accent);margin:0 0 .5em;}
 .ep-proposal p{font-size:var(--t-small);margin:.5em 0;color:var(--fg);}
 .ep-proposal small{display:block;font-size:var(--t-caption);color:var(--muted);margin-bottom:1em;}
 .ep-proposal hr{border:0;border-top:1px solid var(--detail);margin:1em 0;}
 `);
 const stack=(left,top,label,step)=>`<div class="ep-stack reveal-in" data-from="${step}" style="left:${left}%;top:${top}%"><div class="ep-paper"></div><div class="ep-paper"></div><div class="ep-paper"><i></i><i></i><i></i></div><div class="ep-stack-label">${label}</div></div>`;
 frame.innerHTML=`<h2 class="deck-heading">Use what’s known to design what we test next</h2>
 <div class="ep-diagram">
 <svg class="ep-lines" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true">
 <defs><marker id="ep-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="var(--muted)"/></marker></defs>
 <g><path class="ep-edge" d="M90 80 L280 200 M90 200 L280 200 M90 320 L280 200"/></g>
 <g class="reveal-in" data-from="2"><path class="ep-flow" stroke-dasharray="4 5" d="M205 120 Q280 40 435 65"/><path class="ep-flow" d="M190 115 L205 115 L205 285 L190 285"/></g>
 <g class="reveal-in" data-from="4"><path class="ep-flow" marker-end="url(#ep-arrow)" d="M610 75 Q655 75 690 180 L715 180"/><path class="ep-flow" marker-end="url(#ep-arrow)" d="M610 280 Q655 280 690 220 L715 220"/></g>
 </svg>
 <div class="ep-label" style="left:0;top:-7%;width:20%">Related compounds</div>
 <div class="ep-node" style="left:9%;top:20%">A</div><div class="ep-node" style="left:9%;top:50%">B</div><div class="ep-node" style="left:9%;top:80%">C</div>
 <div class="ep-node ep-strain" style="left:28%;top:50%">Y</div>
 <div class="ep-label" style="left:22%;top:64%;width:18%"><strong>Strain of interest</strong></div>
 <div class="ep-label" style="left:0;top:96%;width:37%">Known activity</div>
 ${stack(44,4,'Supporting papers',2)}
 ${stack(44,57,'Protocol templates',3)}
 <div class="ep-proposal reveal-in" data-from="4"><h3>Proposal</h3><small>Compound X · supplied strains</small><p>Assay &amp; readout</p><p>Concentration series</p><p>Controls &amp; replicates</p><hr><p>Rationale &amp; citations</p></div>
 </div>`;
 return {enter(step,animate){Deck.show(frame,step,animate);}};
 }
});
}
