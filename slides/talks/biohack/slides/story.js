// Story framing: 1 researcher and decision; 2 immediate value; 3 contribution and scope.
{
// TODO(final): validate researcher time savings, commensal selectivity and comparative workflow benefit;
// these are explicitly presented as goals, not measured outcomes.
Deck.slide('story', {
  steps: 3,
  notes: 'Our immediate end-user is an antimicrobial discovery researcher moving a candidate from a virtual '
    + 'screen into experimental testing. Given a researcher-selected species panel, the question is how to '
    + 'measure pathogen inhibition and effects on commensals with an appropriate MIC experiment. '
    + 'The intended immediate benefit is less manual translation from evidence to a reviewable assay plan; '
    + 'time savings and biological selectivity have not been measured. Species-panel recommendation is a '
    + 'future extension, not an implemented capability claimed here. MIC means minimum inhibitory concentration. '
    + 'Our contribution is the combination of biological evidence, protocol knowledge and explicit lab constraints '
    + 'in one traceable workflow. We do not claim a new foundation model or a demonstrated first-in-industry algorithm. '
    + 'Industry context: Benchling offers AI experimental design and instrument-connected automation; Opentrons '
    + 'Protocol Designer creates executable robot protocols. Our proposed distinction is the focused antimicrobial '
    + 'evidence-to-assay handoff, to be evaluated rather than asserted as superior. Sources: '
    + 'https://www.benchling.com/ai/experimental-design ; https://www.benchling.com/automation ; '
    + 'https://docs.opentrons.com/protocol-designer/ . '
    + 'Commensal-sparing is an illustrative goal, not a validated result. Sparse commensal measurements and '
    + 'species-specific culture and oxygen requirements limit what can be inferred or executed. '
    + 'Patient benefit is a longer-term motivation; this prototype supports research decisions.',
  mount(frame, { css }) {
    css(`
      .st-question { position: absolute; left: 4.2%; top: 19%; width: 88%; margin: 0;
        font-size: var(--t-lead); line-height: 1.3; }
      .st-rows { position: absolute; left: 4.2%; right: 4.2%; top: 33%; }
      .st-row { display: grid; grid-template-columns: 23% 1fr; column-gap: 3%;
        padding: .4em 0; border-top: 1px solid var(--detail); font-size: var(--t-body); }
      .st-label { color: var(--accent); font-weight: 700; }
      .st-copy { margin: 0; line-height: 1.3; }
      .st-copy small { display: block; margin-top: .35em; font-size: var(--t-small); color: var(--muted); }
    `);
    frame.innerHTML = `
      <h2 class="deck-heading">A testable plan for an antimicrobial candidate</h2>
      <p class="st-question reveal-in" data-from="1">Which experiment will tell us whether a candidate inhibits
        pathogens while sparing commensals?</p>
      <div class="st-rows">
        <div class="st-row reveal-in" data-from="1">
          <div class="st-label">For the researcher</div>
          <p class="st-copy">Antimicrobial discovery scientists testing a candidate.
            <small>Activity against a pathogen alone does not answer the selectivity question.</small></p>
        </div>
        <div class="st-row reveal-in" data-from="2">
          <div class="st-label">Immediate benefit</div>
          <p class="st-copy">A cited MIC plan for a chosen panel, checked for lab feasibility.
            <small>Goal: less manual translation from evidence to OT-2 preparation.</small></p>
        </div>
        <div class="st-row reveal-in" data-from="3">
          <div class="st-label">Our contribution</div>
          <p class="st-copy">Biological evidence + protocol knowledge + lab constraints.
            <small>The proposed distinction is a traceable antimicrobial evidence-to-assay handoff.</small></p>
        </div>
      </div>
      <p class="deck-caption reveal-in" data-from="3">Research prototype · commensal-sparing is illustrative · benefit and comparative performance remain to be measured</p>`;
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
}
