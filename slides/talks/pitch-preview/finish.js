// Three slides: actual pilot results; a timed evidence walkthrough; concise close + Q/A exit.
{
Deck.slide('pitch-results', {steps:4,
 notes:'3:00–4:15. Four beats: test setup; three assessment criteria; a shortened version of the actual case-1 question; then the results figure. The original case-1 prompt additionally asks for an ordered procedure and justified parameters and forbids remembered potency. In a benchmark simulation, known query-pair evidence and its source documents are excluded from fixed input packets. Five models each produce one response on three manually selected, correlated kinase/cell cases. Generation uses those fixed packets, with no live graph retrieval. Grade experiment suitability, procedural soundness and numerical soundness, 0–2 each per case. Scores are provisional, unblinded, uncalibrated Codex judgments, not expert validation or pass rates. No statistical ranking, deterministic baseline, measured KG lift or MIC end-to-end result is established. Models: Kimi K3.1 Pro, GLM 5.3 (not Flash), DeepSeek V4.1 Flash 1017, Nemotron 3 Super, GPT-OSS-120B. Concrete finding, in plain language: one DeepSeek response told the researcher to prepare 11 different concentrations, but the same response listed 10 in its experiment settings. A person would need to resolve that disagreement before using the proposal. Protocol steps here are seven manually generalized benchmark cards with parameter slots and prerequisites, not raw graph nodes or automatically extracted paper protocols. Full presenter script: speaker-notes.html. Sources: biohack/data/pilot_results.json and committed benchmark/runs outputs. Keep detailed axis scores and limitations for Q/A.',
 mount(frame,{data,esc,css}) {
 const d=data.pilotResults;
 css(`
 .pf-intro{position:absolute;inset:20% 7% 12%;}
 .pf-test{font-size:var(--t-body);line-height:1.4;margin:0;width:94%;}
 .pf-test strong{color:var(--accent);}
 .pf-axes{position:absolute;left:0;right:0;top:32%;display:grid;grid-template-columns:repeat(3,1fr);gap:4%;}
 .pf-axis{border-top:2px solid var(--accent);padding-top:.65em;}
 .pf-axis strong{display:block;font-size:var(--t-body);color:var(--fg);}
 .pf-axis span{display:block;font-size:var(--t-small);color:var(--muted);margin-top:.5em;line-height:1.35;}
 .pf-example{position:absolute;top:68%;left:0;right:0;border-left:3px solid var(--accent);padding-left:1.1em;}
 .pf-example small{font-size:var(--t-caption);color:var(--muted);}
 .pf-example p{font-size:var(--t-body);line-height:1.35;margin:.4em 0;}
 .pf-method{position:absolute;left:7%;right:7%;top:28%;font-size:var(--t-small);color:var(--muted)}
 `);
 frame.innerHTML=`<h2 class="deck-heading">Can the model design the missing experiment?</h2>
 <div class="pf-intro reveal-in" data-show="1 2 3">
 <p class="pf-test"><strong>Hide a known measurement and its source papers.</strong><br>Supply evidence and protocol steps with unfilled parameters.<br>Ask each model to design the missing experiment.</p>
 <div class="pf-axes reveal-in" data-from="2">
 <div class="pf-axis"><strong>Experiment choice</strong><span>Does the assay answer<br>the question?</span></div>
 <div class="pf-axis"><strong>Procedure</strong><span>Are the steps sound<br>and complete?</span></div>
 <div class="pf-axis"><strong>Numbers</strong><span>Are parameters justified<br>and internally consistent?</span></div>
 </div>
 <div class="pf-example reveal-in" data-from="3"><small>EXAMPLE · KINASE BENCHMARK</small><p>Design a concentration–response experiment to measure<br>haspin inhibition by CHEMBL4278808.</p></div>
 </div>`;
 const plot=Deck.groupedBars(frame,{max:18,ticks:3,format:v=>`${v}/18`,series:d.models.map(m=>({key:m.id,label:m.name})),groups:[{key:'total',label:['3 cases · 3 criteria · 0–2 points each · maximum 18'],values:Object.fromEntries(d.models.map(m=>[m.id,m.total]))}],footnote:[]});
 plot.root.classList.add('reveal-in');
 plot.root.dataset.from='4';
 frame.insertAdjacentHTML('beforeend','<div class="pf-method reveal-in" data-from="4">Same fixed inputs for every model · 3 kinase/cell cases · no live retrieval</div>');
 return{enter:(s,a)=>{Deck.show(frame,s,a);plot.show(s>=4?1:0,a);}};
 }});
Deck.slide('pitch-demo', {interactive:true,
 notes:'4:15–7:15, strict three-minute evidence walkthrough. 0:00–0:30 establish the question and show the supplied case input. 0:30–1:30 inspect retained evidence and step cards in the benchmark-case tab; the withheld answer is reviewer-only. 1:30–2:15 reveal the held-out record and discuss experiment/steps/numbers; open the recorded model output via the link if useful. 2:15–3:00 show the separately generated MIC run sheet/protocol and simulation warnings. This last artifact begins from a hand-written four-species proposal; it is NOT the execution of the model output just shown. Say so explicitly. This is a recorded-artifact walkthrough, not a live agent run. If the UI is slow, use the pre-opened pages; do not run paid model calls during the pitch. No wet-lab outcomes claimed.',
 mount(frame,{css}) {
 css(`.pd-frame{position:absolute;left:4.2%;top:17%;width:91.6%;height:61%;border:1px solid var(--detail)}.pd-links{position:absolute;left:4.2%;right:4.2%;top:80%;font-size:var(--t-small)}.pd-links a{color:var(--accent);margin-right:1em}`);
 frame.innerHTML=`<h2 class="deck-heading">Inspect the evidence, design and checks</h2><iframe class="pd-frame" src="../biohack/graph/index.html" title="Committed graph and benchmark case viewer"></iframe><div class="pd-links"><a href="../biohack/graph/index.html" target="_blank" rel="noopener">Case viewer ↗</a><a href="data/deepseek-case-2.output.json" target="_blank" rel="noopener">Recorded output ↗</a><a href="../biohack/evidence/run_sheet.md" target="_blank" rel="noopener">Separate MIC run sheet ↗</a></div><p class="deck-caption">Recorded case review · MIC execution example starts from a separate hand-written proposal · 3-minute demo</p>`;
 return{enter(){}};
 }});
// TODO(final): hypothesis refinement and ingestion of experimental results are proposed integrations; this diagram is not an end-to-end run.
Deck.slide('pitch-close',{steps:4,
 notes:'7:15–8:15. The accented region identifies our system: evidence lookup and grounded proposal design. The researcher supplies the question and reviews a proposed experiment before the lab runs it. Reveal the existing-answer route, the missing-measurement route, the result feedback loop, then upstream hypothesis refinement. Muted dashed arrows outside the system identify proposed workflow connections, not implemented automation. The feedback loop adds measured results, assay conditions and provenance, including negative results, to the KB. Hypothesis refinement sharpens an existing idea into a testable question. The current connected agent is IC50-based; this conceptual diagram does not establish an end-to-end bacterial run. Existing evidence does not prevent confirmatory experiments. Full script: speaker-notes.html.',
 mount(frame,{css}) {
 css(`
 .cl-description{position:absolute;left:4.2%;right:4.2%;top:16%;font-size:var(--t-body);line-height:1.4;color:var(--muted);}
 .cl-map{position:absolute;left:5%;right:5%;top:30%;height:55%;}
 .cl-map svg{position:absolute;width:100%;height:100%;overflow:visible;}
 .cl-line{fill:none;stroke:var(--accent);stroke-width:2;}
 .cl-external{stroke:var(--muted);}
 .cl-future{stroke:var(--muted);stroke-dasharray:7 6;}
 .cl-zone{fill:var(--accent);fill-opacity:.035;stroke:var(--accent);stroke-opacity:.35;stroke-width:1.5;}
 .cl-system{position:absolute;left:26%;top:4%;font-size:var(--t-small);color:var(--accent);}
 .cl-node{position:absolute;font-size:var(--t-body);line-height:1.25;}
 .cl-node strong{font-weight:600;}
 .cl-node small{display:block;font-size:var(--t-caption);color:var(--muted);margin-top:.5em;line-height:1.3;}
 .cl-branch{position:absolute;font-size:var(--t-caption);color:var(--accent);line-height:1.25;}
 .cl-loop-label{position:absolute;left:42%;top:80%;width:41%;font-size:var(--t-small);color:var(--muted);text-align:center;}
 .cl-upstream{font-size:var(--t-small);color:var(--muted);}
 /* Opacity only: transforms on a reveal wrapper change the containing block of absolute labels. */
 .cl-map [data-from]{opacity:0;transition:opacity .32s ease;}
 .cl-map [data-from].in{opacity:1;}
 .instant .cl-map [data-from]{transition:none;}
 .cl-link{color:var(--muted);}
 `);
 frame.innerHTML=`<h2 class="deck-heading">Propose an experiment—and show why</h2>
 <div class="cl-description">An assay, concentration range, controls and procedure,<br>with supporting evidence for the researcher to review.</div>
 <div class="cl-map">
 <svg viewBox="0 0 1000 450" preserveAspectRatio="none" aria-hidden="true">
 <defs><marker id="cl-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10" fill="var(--accent)"/></marker><marker id="cl-outer-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10" fill="var(--muted)"/></marker></defs>
 <rect class="cl-zone" x="235" y="0" width="520" height="350" rx="10"/>
 <path class="cl-line cl-external" marker-end="url(#cl-outer-arrow)" d="M160 190 H260"/>
 <path class="cl-line" marker-end="url(#cl-arrow)" d="M435 190 H475 V110 H530"/>
 <path data-from="2" class="cl-line" marker-end="url(#cl-arrow)" d="M475 190 V270 H530"/>
 <path data-from="2" class="cl-line cl-external" marker-end="url(#cl-outer-arrow)" d="M710 270 H825"/>
 <path data-from="3" class="cl-line cl-future" marker-end="url(#cl-outer-arrow)" d="M910 355 V430 H340 V255"/>
 <path data-from="4" class="cl-line cl-future" marker-end="url(#cl-outer-arrow)" d="M70 80 V150"/>
 </svg>
 <div class="cl-system">Our system</div>
 <div class="cl-node" style="left:0;top:35%;width:17%"><strong>Researcher’s<br>question</strong></div>
 <div class="cl-node" style="left:27%;top:35%;width:19%"><strong>Check the<br>knowledge base</strong></div>
 <div class="cl-branch" style="left:54%;top:12%">Answer exists</div>
 <div class="cl-node" style="left:54%;top:22%;width:20%"><strong>Return result<br>and sources</strong></div>
 <div class="cl-branch" data-from="2" style="left:54%;top:46%">Measurement missing</div>
 <div class="cl-node" data-from="2" style="left:54%;top:57%;width:20%"><strong>Propose an<br>experiment</strong></div>
 <div class="cl-node" data-from="2" style="left:84%;top:49%;width:17%"><small>Researcher / lab</small><strong>Review<br>and run</strong></div>
 <div class="cl-loop-label" data-from="3">Add measured results<br>and sources to the KB</div>
 <div class="cl-node cl-upstream" data-from="4" style="left:0;top:0;width:22%"><strong>Hypothesis<br>refinement</strong></div>
 </div>
 <p class="deck-caption"><a class="cl-link" href="qa.html" target="_blank" rel="noopener">Q/A backup ↗</a></p>`;
 return{enter(s,a){Deck.show(frame,s,a);}};
 }});
}
