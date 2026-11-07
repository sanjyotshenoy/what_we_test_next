// The title slide, laid out like the organisers' template (Nucleate Pittsburgh BioHack 2026, NVIDIA challenge):
// img/title_bg.webp is their slide with the text taken out, so the gradient, wave and logos are theirs and
// every word here is live text. No section, so no footer. One step: everything is there on arrival.
Deck.slide('title', {
  notes: 'BioTech Track, challenge 2: Multi-Omics. How can we prototype agentic frameworks that leverage GNNs '
    + 'to parse phenotype-genotype knowledge graphs?',
  mount(frame, { css, esc }) {
    const TITLE = {
      track: 'BioTech Track',
      number: '2',
      title: 'Multi-Omics',
      question: 'How can we prototype agentic frameworks that leverage GNNs to parse phenotype-genotype '
        + 'knowledge graphs?',
    };
    frame.innerHTML = `
      <img class="bh-bg" src="img/title_bg.webp" alt="">
      <p class="bh-track reveal-in" data-from="1">${esc(TITLE.track)}</p>
      <p class="bh-number reveal-in" data-from="1">${esc(TITLE.number)}</p>
      <h1 class="bh-title reveal-in" data-from="1" style="--i:1">${esc(TITLE.title)}</h1>
      <p class="bh-question reveal-in" data-from="1" style="--i:2">${esc(TITLE.question)}</p>`;
    // The background is a fixed light picture in both themes, so the text keeps the template's black rather
    // than var(--fg) (which turns light in the dark theme). Positions and sizes are measured off the template.
    css(`.bh-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      .deck-frame .bh-track, .deck-frame .bh-number, .deck-frame .bh-title, .deck-frame .bh-question {
        position: absolute; margin: 0; color: #000; font-weight: 400; line-height: 1; }
      .deck-frame .bh-track { right: 3.2%; top: 2.6%; font-size: var(--t-caption); }
      .deck-frame .bh-number { left: 88.3%; top: 12.4%; font-size: calc(4.15 * var(--u)); }
      .deck-frame .bh-title { left: 6.4%; top: 42.9%; font-size: calc(4.35 * var(--u)); }
      .deck-frame .bh-question { left: 6.45%; top: 54.6%; width: 86%; font-size: calc(2.5 * var(--u)); line-height: 1.3;
        text-transform: uppercase; }
      /* the slide number would sit on the BioHack logo */
      html:has(section[data-slide="title"].present) .reveal .slide-number { visibility: hidden; }`);
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
