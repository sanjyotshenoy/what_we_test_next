// The live demo, embedded: the demo page (../demo/, a trace of one query through the pipeline) in a frame under
// the heading. Interactive, so clicks and scrolls stay in the page; click outside the frame or use the arrow
// keys (after clicking the slide's margin) to move on. It takes the place of the "Demo" placeholder, which stays
// in blank.js but is hidden. Load with Deck.section(4) before it. One step.
Deck.slide('demo', {
  before: 'blank-8',
  interactive: true,
  notes: 'Type or pick the query and press Run: the stages play one by one, or press Show all. Full screen: open '
    + 'demo/ in its own tab. The numbers are a mock trace until the agent writes real ones.',
  mount(frame, { css, esc, theme }) {
    css(`.deck-frame .dm-frame { position: absolute; left: 4.2%; top: 15%; width: 91.6%; height: 72%;
        border: 1px solid color-mix(in srgb, var(--muted) 25%, transparent); border-radius: calc(.8 * var(--u));
        background: var(--bg); }
      .deck-frame .dm-open { position: absolute; left: auto; right: 4.2%; top: 7%; font-size: var(--t-small);
        color: var(--accent); }`);
    frame.innerHTML = `<h2 class="deck-heading reveal-in in">${esc('Demo: one query, start to finish')}</h2>
      <a class="dm-open" href="demo/" target="_blank" rel="noopener">open full screen ↗</a>
      <iframe class="dm-frame" src="demo/index.html?theme=${esc(theme)}" title="Demo"></iframe>`;
    return { enter() {} };
  },
});
Deck.hide('blank-7');
