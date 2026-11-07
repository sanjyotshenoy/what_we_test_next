// The title slide: the deck's usual title layout on a wavy background (img/wave.webp, 3840x2160), with the
// team's names as the byline. No section, so no footer. One step: everything is there on arrival.
Deck.slide('title', {
  notes: 'Title slide.',
  mount(frame, { css, esc }) {
    const TITLE = {
      title: 'Closing the Loop Between Knowledge and Discovery',
      subtitle: 'Nucleate Pittsburgh BioHack 2026',
      team: 'Team Zhang et al.',
      names: ['Sanjyot Shenoy', 'Seh Na Mellick', 'Jimmy Hsu', 'Aidan Zhang', 'Xiaochen Zhai',
        'Ramith Hettiarachchi', 'Emmy Nguyen'],
    };
    frame.innerHTML = `
      <img class="ti-bg" src="img/wave.webp" alt="">
      <h1 class="deck-title ti-title reveal-in" data-from="1">${esc(TITLE.title)}</h1>
      <p class="deck-subtitle ti-subtitle reveal-in" data-from="1" style="--i:1">${esc(TITLE.subtitle)}</p>
      <p class="ti-team reveal-in" data-from="1" style="--i:2">${esc(TITLE.team)}</p>
      <p class="ti-names reveal-in" data-from="1" style="--i:2">${TITLE.names.map(n => `<span>${esc(n)}</span>`).join('')}</p>`;
    // the title and names stay left of the wave; the picture is light, so the dark theme flips its lightness
    // and keeps its hues, and var(--fg) text reads on both
    css(`.ti-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      :root[data-theme="dark"] .ti-bg { filter: invert(1) hue-rotate(180deg) brightness(.9); }
      .deck-frame .ti-title { top: 16%; width: 60%; text-wrap: balance; }
      .deck-frame .ti-subtitle { top: 40%; width: 60%; }
      .ti-team { position: absolute; left: 8%; top: 54%; margin: 0; font-size: var(--t-small); font-weight: 700;
        color: var(--accent); }
      .ti-names { position: absolute; left: 8%; top: 59.5%; width: 50%; margin: 0; display: flex; flex-wrap: wrap;
        gap: .45em 1.4em; font-size: var(--t-body); }`);
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
