// The title slide: the deck's usual title layout on a wavy background, with the team's faces and names as the byline.
// No section, so no footer. One step: everything is there on arrival.
//
// The background is SVG drawn here, not a picture: it is sharp at any size, and it covers the whole window
// (not only the 16:9 frame), so full screen on a 16:10 or ultrawide display has no plain bars around it. Its
// colours are the --wv-* variables below, one set per theme.
{
// the wave's edge in a 1600x900 box, traced off the reference slide and run past the box's edges
const EDGE = 'M848,1000 C838,960 833,920 833,879 C833,838 838,796 848,756 C859,711 878,666 901,625 '
  + 'C924,584 954,544 987,511 C1020,478 1059,449 1099,427 C1140,404 1186,392 1230,376 C1274,361 1322,353 1365,335 '
  + 'C1407,317 1448,295 1487,269 C1525,243 1557,210 1595,178 C1634,145 1697,92 1718,75';
const WAVE = `${EDGE} L1800,75 L1800,1100 L848,1100 Z`;
const stop = (offset, v, o = 1) => `<stop offset="${offset}" style="stop-color: var(--wv-${v}); stop-opacity: ${o}"/>`;

// slice: fill the window, cropping the box's edges when the window is not 16:9; the box stays centred
const BACKGROUND = `
  <svg class="wv-bg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="wv-base" gradientUnits="userSpaceOnUse" x1="0" y1="900" x2="1600" y2="0">
        ${stop(0, 'base-1')}${stop(.5, 'base-2')}${stop(1, 'base-3')}
      </linearGradient>
      <radialGradient id="wv-glow" gradientUnits="userSpaceOnUse" cx="1150" cy="330" r="560"
        gradientTransform="translate(1150 330) rotate(-28) scale(1.5 .62) translate(-1150 -330)">
        ${stop(0, 'glow', .95)}${stop(.45, 'glow', .55)}${stop(1, 'glow', 0)}
      </radialGradient>
      <radialGradient id="wv-corner" gradientUnits="userSpaceOnUse" cx="1600" cy="0" r="420">
        ${stop(0, 'corner', .9)}${stop(1, 'corner', 0)}
      </radialGradient>
      <radialGradient id="wv-fill" gradientUnits="userSpaceOnUse" cx="1560" cy="600" r="820">
        ${stop(0, 'fill-1')}${stop(.4, 'fill-2')}${stop(1, 'fill-3')}
      </radialGradient>
      <linearGradient id="wv-floor" gradientUnits="userSpaceOnUse" x1="0" y1="450" x2="0" y2="900">
        ${stop(0, 'floor', 0)}${stop(1, 'floor')}
      </linearGradient>
      <clipPath id="wv-clip"><path d="${WAVE}"/></clipPath>
      <filter id="wv-soft" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="7"/></filter>
    </defs>
    <rect x="-200" y="-200" width="2000" height="1300" fill="url(#wv-base)"/>
    <rect x="-200" y="-200" width="2000" height="1300" fill="url(#wv-glow)"/>
    <rect x="-200" y="-200" width="2000" height="1300" fill="url(#wv-corner)"/>
    <path d="${WAVE}" fill="url(#wv-fill)"/>
    <path d="${WAVE}" fill="url(#wv-floor)"/>
    <g clip-path="url(#wv-clip)">
      <path d="${EDGE}" fill="none" stroke-width="26" filter="url(#wv-soft)"
        style="stroke: var(--wv-rim); stroke-opacity: var(--wv-rim-o)"/>
    </g>
  </svg>`;

Deck.slide('title', {
  notes: 'Open with the researcher’s decision: given a hypothesis, what experiment should we run next? Our motivating user is a microbiome researcher testing whether a supplied compound inhibits a pathogen while sparing commensals. We propose evidence-grounded experiments for researcher review; selective inhibition is the hypothesis, not a demonstrated outcome.',
  mount(frame, { css, esc }) {
    const TITLE = {
      title: 'Given a hypothesis, what experiment should we run next?',
      subtitle: 'Helping microbiome researchers test whether a compound inhibits a pathogen while sparing commensal bacteria.',
      team: 'Team Zhang et al.',
      track: '(Biotech Track: Problem #2)',
      names: ['Aidan Zhang', 'Emmy Nguyen', 'Jimmy Hsu', 'Ramith Hettiarachchi', 'Sanjyot Shenoy',   // by first name
        'Seh Na Mellick', 'Xiaochen Zhai'],
    };
    // headshots in data/team/<first-last>.jpg (360 px squares; from the CMU CPCB students page, Emmy's, Jimmy's and Xiaochen's supplied by the team). Add a name here
    // once its file is there; the rest show their initials.
    const PHOTOS = new Set(['Aidan Zhang', 'Emmy Nguyen', 'Jimmy Hsu', 'Ramith Hettiarachchi', 'Sanjyot Shenoy', 'Seh Na Mellick', 'Xiaochen Zhai']);
    const face = (n) => {
      const words = n.split(' ');
      const last = words.pop(), first = words.join(' ');   // "Seh Na" / "Mellick"
      const pic = PHOTOS.has(n)
        ? `<img src="../biohack/data/team/${n.toLowerCase().replace(/ /g, '-')}.jpg" alt="">`
        : `<span class="ti-initials">${esc(first[0] + last[0])}</span>`;
      return `<figure class="ti-face">${pic}<figcaption>${esc(first)}<br>${esc(last)}</figcaption></figure>`;
    };
    frame.innerHTML = `${BACKGROUND}
      <h1 class="deck-title ti-title reveal-in" data-from="1">${esc(TITLE.title)}</h1>
      <p class="ti-project reveal-in" data-from="1" style="--i:1">Project Ouroboros</p>
      <p class="deck-subtitle ti-subtitle reveal-in" data-from="1" style="--i:1">${esc(TITLE.subtitle)}</p>
      <p class="ti-team reveal-in" data-from="1" style="--i:2">${esc(TITLE.team)}</p>
      <p class="ti-track reveal-in" data-from="1" style="--i:2">${esc(TITLE.track)}</p>
      <div class="ti-names reveal-in" data-from="1" style="--i:2">${TITLE.names.map(face).join('')}</div>`;
    // the background is centred on the frame and sized to the window, under everything else on the slide
    css(`.wv-bg { position: absolute; left: 50%; top: 50%; width: 100vw; height: 100vh; transform: translate(-50%, -50%);
        pointer-events: none; }
      :root { --wv-base-1: #dfe3e6; --wv-base-2: #d2dce6; --wv-base-3: #a9d0e2; --wv-glow: #6fb8dc; --wv-corner: #8dceda;
        --wv-fill-1: #e2f6fe; --wv-fill-2: #c8eafb; --wv-fill-3: #a3d4f1; --wv-floor: #d4e5f3; --wv-rim: #f4fbff;
        --wv-rim-o: .8; }
      :root[data-theme="dark"] { --wv-base-1: #0f1218; --wv-base-2: #121a24; --wv-base-3: #173144; --wv-glow: #1d5d84;
        --wv-corner: #1f6470; --wv-fill-1: #0b1824; --wv-fill-2: #0e2232; --wv-fill-3: #133149; --wv-floor: #0d1520;
        --wv-rim: #6cbde9; --wv-rim-o: .35; }
      .deck-frame .ti-title { top: 11%; width: 84%; font-size: var(--t-heading); text-wrap: balance; }
      .ti-project { position: absolute; left: 8%; top: 27%; margin: 0; font-size: var(--t-body); font-weight: 600; color: var(--accent); }
      .deck-frame .ti-subtitle { top: 38%; width: 78%; font-size: var(--t-body); line-height: 1.4; }
      /* the team's name sits large on the wave, bottom right */
      .ti-team { position: absolute; right: 7%; top: 68%; margin: 0; font-size: var(--t-heading); font-weight: 700;
        color: var(--accent); white-space: nowrap; }
      .ti-track { position: absolute; right: 7%; top: 76%; margin: 0; font-size: var(--t-body); color: var(--muted);
        white-space: nowrap; }
      /* the team, four to a row: a round headshot (or initials) over the first and last name */
      .ti-names { position: absolute; left: 8%; top: 53%; width: 44%; margin: 0; display: grid;
        grid-template-columns: repeat(4, 1fr); gap: calc(1.2 * var(--u)) 0; }
      .ti-face { margin: 0; display: flex; flex-direction: column; align-items: center; text-align: center; }
      .ti-face img, .ti-initials { width: calc(5.8 * var(--u)); height: calc(5.8 * var(--u)); border-radius: 50%;
        object-fit: cover; box-shadow: 0 0 0 calc(.25 * var(--u)) color-mix(in srgb, var(--bg) 85%, transparent); }
      .ti-initials { display: grid; place-items: center; font-weight: 700; font-size: var(--t-small); color: var(--accent);
        background: color-mix(in srgb, var(--accent) 14%, var(--bg)); }
      .ti-face figcaption { margin-top: calc(.5 * var(--u)); font-size: var(--t-micro); line-height: 1.15; }`);
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
}
