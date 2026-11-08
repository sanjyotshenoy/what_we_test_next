// Repository evidence: graph, rules, computed plate, verification, pilot and integration boundary.
// Values come from prep_deck_evidence.py; no model scores or wet-lab outcomes are synthesized.
{
const source = 'Repository audit: main 30886d3 (2026-11-08). ';
function add(name, section, heading, body, caption, notes) {
  Deck.section(section);
  Deck.slide(name, { before: name === 'evidence-pilot' ? 'evidence-verification' : undefined, notes: source + notes, mount(frame, { css, esc, data }) {
    css(`
      .ev-body { position:absolute; left:4.2%; right:4.2%; top:19%; font-size:var(--t-body); line-height:1.35; }
      .ev-big { font-size:var(--t-display); font-weight:700; color:var(--accent); line-height:1.1; }
      .ev-lead { font-size:var(--t-lead); margin:.5em 0; }
      .ev-body p { margin:.65em 0; }
      .ev-body small { font-size:var(--t-small); color:var(--muted); }
      .ev-split { display:grid; grid-template-columns:38% 1fr; gap:6%; align-items:start; }
      .ev-table { width:100%; border-collapse:collapse; font-size:var(--t-small); }
      .ev-table th,.ev-table td { text-align:left; padding:.6em .45em; border-bottom:1px solid var(--detail); vertical-align:top; }
      .ev-table th { color:var(--accent); }
      .ev-plate { width:100%; border-collapse:collapse; font-size:var(--t-caption); }
      .ev-plate th,.ev-plate td { padding:.45em .25em; text-align:center; border-bottom:1px solid var(--detail); }
      .ev-plate th:first-child,.ev-plate td:first-child { text-align:left; }
      .ev-note { color:var(--muted); font-size:var(--t-small); }
      .ev-links a { color:var(--accent); margin-right:1.3em; }
      .ev-callout { margin-top:1em; padding-top:.6em; border-top:1px solid var(--detail); }
    `);
    frame.innerHTML=`<h2 class="deck-heading">${esc(heading)}</h2><div class="ev-body">${body(data.evidence,esc)}</div><p class="deck-caption">${esc(caption)}</p>`;
    return { enter() {} };
  }});
}
add('evidence-graph',2,'A measured-data graph, with provenance', (d)=>`
  <div class="ev-split"><div><div class="ev-big">${d.graph.edges.toLocaleString()}</div><p class="ev-lead">MIC measurements</p><p>${d.graph.types.Compound} compounds · ${d.graph.types.Organism} species</p><small>Built from the local ChEMBL 37 database.</small></div>
  <div><p>Every measurement retains its assay, document, unit and relation.</p><p><strong>${d.graph.censored.toLocaleString()} censored results preserved.</strong><br><code>&gt;128</code> means the threshold was not reached; it is not an exact MIC.</p><p class="ev-note">Commensal-first retrieval creates paired evidence. Species-level records can still hide resistant strains.</p></div></div>
  <p class="ev-links ev-callout"><a href="../biohack/evidence/mic_examples.json" target="_blank" rel="noopener">Inspect MIC source records ↗</a></p>`,
  '25,632 nodes · 21,640 assays · 3,387 documents · counts recomputed from committed CSVs',
  'Sources: kg/biology/build_bacteria.py, chembl_bacteria_db.py, graph_bacteria/{nodes,edges}.csv. No benchmark hold-out applied to this MIC graph. Traits are hand-curated. A high MIC in one resistant isolate does not prove commensal sparing. The separate explorer contains kinase/protocol data, not the bacterial MIC graph.');
add('evidence-rules',2,'Protocol choices have inspectable sources',d=>`
  <div class="ev-split"><div><div class="ev-big">${d.rules.total}</div><p class="ev-lead">sourced design rules</p><p>${d.rules.checkable} have executable checks</p></div><div><p><strong>3 curated templates</strong> carry steps, parameters, controls and source evidence.</p><p>Defaults retain their observations and derivation; disagreements are flagged.</p><p class="ev-note">The graph spans 8 assay archetypes. Much of the rule set is enzyme-focused; MIC applicability needs review.</p></div></div>
  <p class="ev-callout">The researcher can inspect <strong>why a parameter was chosen</strong>, then accept or revise it.</p>`,
  'Sources: Assay Guidance Manual, PubChem BioAssay and the team’s MIC reference protocol',
  'kg/protocols/rules.yaml, templates/*.json, defaults.py and build_db.py. Curated content has not received full human review. extract.py is tested with a stubbed client, not evidence of completed bulk LLM extraction. Keep routing mechanics high-level; show source-linked values when challenged.');
add('evidence-plate',2,'The plate is computed—and independently audited',(d,esc)=>{
 const names={'Clostridioides difficile':'C. difficile','Enterococcus faecalis':'E. faecalis','Bacteroides fragilis':'B. fragilis','Bifidobacterium longum':'B. longum'};
 const rows=[...new Set(d.plate.wells.map(w=>w.row))];
 return `<p class="ev-note">Hand-written MIC example · 4 species × 2 replicates · final concentrations in µg/mL</p><table class="ev-plate"><thead><tr><th>Row / species</th>${Array.from({length:10},(_,i)=>`<th>${i+1}</th>`).join('')}<th>GC</th><th>SC</th></tr></thead><tbody>${rows.filter((_,i)=>i%2===0).map(r=>{const ws=d.plate.wells.filter(w=>w.row===r);return `<tr><td>${r}–${String.fromCharCode(r.charCodeAt(0)+1)} · ${esc(names[ws[0].species]||ws[0].species)}</td>${ws.map(w=>`<td>${w.role==='growth control'?'GC':w.role==='sterility control'?'SC':w.final_uM}</td>`).join('')}</tr>`;}).join('')}</tbody></table>
 <p class="ev-lead"><strong>512 µg/mL prepared → 256 µg/mL after inoculum.</strong></p><p class="ev-note">The audit replays transfers to catch a plausible-looking 2× error. GC: growth control; SC: sterility control.</p>`;},
 'Generated from execution/examples/mic_selectivity.jsonl · audit: 0 disagreements for this two-fold example',
 'execution/plate.py: plate_design and audit use separate arithmetic. The example is hand-written, not agent-generated. Internal historical field names say uM, but design.unit supplies ug/mL. Non-two-fold transfers are not implemented correctly; an audit warning is not yet a hard stop. Species/media compatibility still needs expert review.');
add('evidence-verification',4,'A protocol that passes the simulator',d=>`
 <table class="ev-table"><thead><tr><th>Check run for this review</th><th>Observed result</th></tr></thead><tbody>
 <tr><td>Repository test suite at main 30886d3</td><td><strong>340 passed · 3 skipped</strong></td></tr>
 <tr><td>Four-species example → OT-2 protocol</td><td><strong>${d.simulation.simulated_ok?'Simulation passed':'Not verified'}</strong> · Opentrons 8.8.2 · API ${d.simulation.api_level}</td></tr>
 <tr><td>Independent transfer replay</td><td>${d.audit_errors.length} plate-audit disagreements for this example</td></tr>
 </tbody></table><p>Two outputs: <strong>robot code + human run sheet</strong>.<br><small>Incubation, readout and MIC calling remain off-robot steps.</small></p>
 <p class="ev-links"><a href="../biohack/evidence/protocol.py" download>Generated protocol ↓</a><a href="../biohack/evidence/run_sheet.md" target="_blank">Run sheet ↗</a><a href="../biohack/evidence/result.json" target="_blank">Result + warnings ↗</a></p>`,
 'Software verification, not wet-lab validation · pipette installation and anaerobic incubation remain unconfirmed',
 'Reproduced 2026-11-08. pytest: 340 passed, 3 skipped, with no LLM calls. Separate execution.generate --simulate run used the committed hand-written example, opentrons==8.8.2 and numpy<2. Simulation validates executable robot operations, not biological efficacy. Exact input and warnings are downloadable under evidence/.');
add('evidence-pilot',3,'Three auditable evaluation cases',()=>`
 <table class="ev-table"><thead><tr><th>Existing case packet</th><th>What it probes</th></tr></thead><tbody>
 <tr><td>Haspin biochemical inhibition · case 1</td><td>Low-concentration coverage</td></tr><tr><td>Haspin biochemical inhibition · case 2</td><td>Parameter choice for a different reference potency</td></tr><tr><td>Rec-1 cell viability · case 3</td><td>Cellular effect ≠ target-specific inhibition</td></tr></tbody></table>
 <p>Input evidence and reviewer-only answers are separate. The packet builder excludes the query pair and its documents.</p><p class="ev-note">These are kinase/cell cases. The following slides show provisional model scores; a validated MIC benchmark remains open.</p>
 <p class="ev-links"><a href="../biohack/graph/index.html" target="_blank" rel="noopener">Inspect the cases and answer toggles ↗</a></p>`,
 'Three manually selected diagnostic cases · reviewer calibration and source-leakage review still required',
 'slides/talks/biohack/graph/BENCHMARK.md and slides/tools/prep_benchmark_cases.py. Cases are not independent samples for a generalization claim. Runtime graph masking is not wired into the agent. Structured step output extends the current agent contract. Completed fixed-packet pilot: DeepSeek V4.1 Flash 1017, Kimi K3.1 Pro, GLM 5.3 (not Flash), Nemotron 3 Super, and GPT-OSS-120B. The following slides show provisional Codex grades; this is not an agent retrieval comparison.');
add('evidence-boundary',4,'What is built, and what still needs connecting',()=>`
 <table class="ev-table"><thead><tr><th>Implemented and inspectable</th><th>Still to establish</th></tr></thead><tbody>
 <tr><td>MIC graph with provenance and censored measurements</td><td>MIC-aware agent retrieval; current helper defaults to kinase IC50</td></tr>
 <tr><td>Protocol templates, sourced rules and parameter derivations</td><td>Domain review of MIC routing and culture conditions</td></tr>
 <tr><td>Computed plate map, independent audit, simulated OT-2 example</td><td>Hard audit gates, non-two-fold support and confirmed hardware</td></tr>
 <tr><td>Five-model diagnostic pilot and extensive software tests</td><td>Independent grading, measured time savings and biological validation</td></tr></tbody></table>`,
 'Claim today: inspectable components and a verified execution example · not an autonomous MIC discovery loop',
 'Audit of agent/README.md, kg/biology/README.md, execution/README.md, benchmark/README.md and graph/BENCHMARK.md at main 30886d3. Unknown oxygen tolerance currently passes optimistically. The earlier animated trace includes mock execution/validation and is deliberately not the central proof in this deck.');
add('evidence-next',6,'The next proof is one connected MIC experiment',()=>`
 <p class="ev-lead">Take a candidate and a researcher-selected panel through the full chain.</p>
 <table class="ev-table"><tbody><tr><th>Connect</th><td>MIC-aware retrieval → sourced assay design → audited protocol</td></tr><tr><th>Challenge</th><td>Withheld measurements, wrong endpoints, bad units and infeasible conditions</td></tr><tr><th>Measure</th><td>Researcher review time, design correctness and reproducibility</td></tr></tbody></table>
 <p class="ev-callout"><strong>Our proposed contribution:</strong> a traceable link between biological evidence and an experiment the lab can review and run.</p>`,
 'Patient benefit motivates the work; the immediate deliverable supports a research decision.',
 'Proposed next experiments, not completed results. Keep architecture high-level; foreground the auditable artifacts and measured checks. Industry alternatives already provide experimental design and automation; superiority of this combination remains to be tested.');
Deck.section(null);
}
