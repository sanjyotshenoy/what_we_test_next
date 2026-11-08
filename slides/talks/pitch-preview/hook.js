// One hook, two clicks: concrete research question, then the question-to-experiment gap.
{
Deck.slide('pitch-hook', {steps:2,
 notes:'0:00–0:50. Start with a researcher who already has compound X and specified bacterial strains. The desired experiment tests pathogen inhibition and commensal preservation. Compound discovery and strain choice are upstream. The gap is turning a research question into a justified experiment. Do not claim that industry lacks experimental design or automation. Selectivity is a research objective, not a clinical outcome demonstrated by this prototype. Team Zhang et al., Nucleate Pittsburgh BioHack 2026.',
 mount(frame,{css}) {
 css(`.ph-question{position:absolute;left:7%;right:7%;top:22%;font-size:var(--t-lead);line-height:1.35}.ph-question strong{color:var(--accent)}.ph-gap{position:absolute;left:7%;right:7%;top:48%;font-size:var(--t-lead);line-height:1.35}.ph-gap strong{display:block;color:var(--accent);margin-bottom:.6em}.ph-small{display:block;font-size:var(--t-small);color:var(--muted);margin-top:.7em}`);
 frame.innerHTML=`<h2 class="deck-heading">What should we test next?</h2><div class="ph-question">“Will <strong>compound X</strong> inhibit the pathogen<br>while sparing the commensals in my panel?”<span class="ph-small">The researcher brings the compound, specified strains and question.</span></div><div class="ph-gap reveal-in" data-from="2"><strong>The gap: turning a research question<br>into a justified experiment.</strong>Which assay, which steps, which parameters—and can this lab run it?</div><p class="deck-caption">Team Zhang et al. · Nucleate Pittsburgh BioHack 2026 · research prototype</p>`;
 return{enter:(s,a)=>Deck.show(frame,s,a)};
 }});
}
