// Stakes: 1 collateral damage; 2 published proof of concept; 3 the research decision we support.
{
Deck.slide('why', {
  steps: 3,
  notes: 'Open with the consequence: an antibiotic can inhibit a pathogen while also disrupting gut bacteria '
    + 'that help resist colonization by opportunistic pathogens. Pathogen potency alone does not establish '
    + 'microbiome preservation. This motivates measuring both sides early in discovery. '
    + 'Published proof of concept: Muñoz et al., A Gram-negative-selective antibiotic that spares the gut '
    + 'microbiome, Nature 630, 429–436 (2024), doi:10.1038/s41586-024-07502-0. '
    + 'https://www.nature.com/articles/s41586-024-07502-0 ; https://pubmed.ncbi.nlm.nih.gov/38811738/ . '
    + 'The authors report activity against more than 130 multidrug-resistant clinical isolates and efficacy '
    + 'in mouse infection models, with microbiome preservation and prevention of secondary C. difficile infection '
    + 'in mice. These are separate in-vitro and animal findings, not human efficacy or results from our system. '
    + 'Our researcher supplies a candidate and specified bacterial strains; selecting either is upstream. The proposed workflow connects available '
    + 'biological evidence to an appropriate concentration series, culture requirements and a lab-feasible MIC '
    + 'plan. A panel MIC assay is an early selectivity screen; it cannot establish whole-microbiome safety, '
    + 'human exposure, clinical benefit or efficacy. The immediate output is a reviewable experiment, '
    + 'and the longer-term motivation is finding candidates with less collateral microbiome damage.',
  mount(frame, { css }) {
    css(`
      .wy-stakes { position: absolute; left: 4.2%; top: 18%; width: 89%; margin: 0;
        font-size: var(--t-lead); line-height: 1.3; }
      .wy-evidence { position: absolute; left: 4.2%; right: 4.2%; top: 37%; display: grid;
        grid-template-columns: 29% 1fr; gap: 5%; align-items: start; }
      .wy-number { font-size: var(--t-display); color: var(--accent); font-weight: 700; line-height: 1; }
      .wy-label { font-size: var(--t-small); margin: .6em 0 0; line-height: 1.3; }
      .wy-evidence h3 { font-size: var(--t-lead); margin: 0 0 .5em; }
      .wy-evidence p { font-size: var(--t-body); margin: 0; line-height: 1.35; }
      .wy-action { position: absolute; left: 4.2%; right: 4.2%; top: 68%; padding-top: .7em;
        border-top: 1px solid var(--detail); font-size: var(--t-lead); line-height: 1.3; }
      .wy-action small { display: block; margin-top: .5em; font-size: var(--t-small); color: var(--muted); }
    `);
    frame.innerHTML = `
      <h2 class="deck-heading">Which bacteria should survive treatment?</h2>
      <p class="wy-stakes reveal-in" data-from="1">Antibiotics can disrupt the gut microbes that help protect us,
        leaving an opening for infections such as <em>C. difficile</em>.</p>
      <div class="wy-evidence reveal-in" data-from="2">
        <div><div class="wy-number">130+</div>
          <div class="wy-label">drug-resistant clinical isolates<br>inhibited by lolamicin <strong>in vitro</strong></div></div>
        <div><h3>A published proof of concept</h3>
          <p>Lolamicin treated infections while preserving the gut microbiome and preventing secondary
            <em>C. difficile</em> infection <strong>in mice</strong>.</p></div>
      </div>
      <div class="wy-action reveal-in" data-from="3"><strong>Our next experiment must test both sides of selectivity.</strong>
        <small>A candidate + specified strains + a question → a grounded experiment design.</small></div>
      <p class="deck-caption">Muñoz et al., Nature (2024) · doi:10.1038/s41586-024-07502-0 · Published evidence, not our results</p>`;
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
}
