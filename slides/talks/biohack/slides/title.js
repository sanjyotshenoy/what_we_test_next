// The title slide: the deck's usual title layout on a wavy background (img/wave.webp, 3840x2160). No section,
// so no footer. The title is there on arrival; the byline joins on the second click.
Deck.slide('title', {
  steps: 2,
  notes: 'Title slide.',
  mount(frame, { css, esc }) {
    const TITLE = {
      title: 'What we test next',
      subtitle: 'Nucleate Pittsburgh BioHack 2026',
      name: 'Ramith Hettiarachchi',
      place: 'Carnegie Mellon University',
      link: 'https://github.com/ramithuh/protein-design-interactive-slides',
    };
    frame.innerHTML = `
      <img class="ti-bg" src="img/wave.webp" alt="">
      <h1 class="deck-title reveal-in" data-from="1">${esc(TITLE.title)}</h1>
      <p class="deck-subtitle reveal-in" data-from="1" style="--i:1">${esc(TITLE.subtitle)}</p>
      <p class="ti-link reveal-in" data-from="1" style="--i:2"><a href="${esc(TITLE.link)}">${esc(TITLE.link.replace(/^https:\/\//, ''))}</a></p>
      <div class="deck-byline reveal-in" data-from="2">${esc(TITLE.name)}<span>${esc(TITLE.place)}</span></div>`;
    // the picture is light; the dark theme flips its lightness and keeps its hues, so var(--fg) text reads on both
    css(`.ti-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      :root[data-theme="dark"] .ti-bg { filter: invert(1) hue-rotate(180deg) brightness(.9); }
      .ti-link { position: absolute; left: 8%; top: 59.5%; margin: 0; font-size: var(--t-body); }
      .ti-link a { color: var(--accent); text-decoration: none; }`);
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
