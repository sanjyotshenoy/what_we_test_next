// The live demo, embedded: the demo page (../demo/, a trace of one query through the pipeline) filling the slide,
// with no heading so the page gets the room. The slide is always dark: it switches the deck to the dark theme while
// it is on screen and back on leaving, and loads the page dark. Interactive, so clicks and scrolls stay in the
// page; click outside the frame (or use the arrow keys after clicking the slide's margin) to move on. It takes the
// place of the "Demo" placeholder, which stays in blank.js but is hidden. Load with Deck.section(5) before it.
// One step.
// TODO(final): drop "mock trace" from the notes once the demo plays a real run.
Deck.slide('demo', {
  before: 'blank-8',
  interactive: true,
  notes: 'Live demo. Type or pick the query and press Run: a stage plays, then waits for Next step (Show all '
    + 'jumps to the end). Full screen: the link at the bottom right opens it in its own tab. The numbers are a '
    + 'mock trace until the agent writes real ones.',
  mount(frame, { css }) {
    css(`.deck-frame .dm-frame { position: absolute; left: 1.5%; top: 2.5%; width: 97%; height: 88%; border: 0;
        border-radius: calc(.6 * var(--u)); background: var(--bg); }
      .deck-frame .dm-open { position: absolute; left: auto; right: 2%; top: 91.5%; font-size: var(--t-micro);
        color: var(--muted); }`);
    frame.innerHTML = `<iframe class="dm-frame" src="demo/index.html?theme=dark" title="Live demo"></iframe>
      <a class="dm-open" href="demo/?theme=dark" target="_blank" rel="noopener">open full screen ↗</a>`;
    const root = document.documentElement;
    return {
      enter() { root.dataset.theme = 'dark'; },
      leave() { root.dataset.theme = Deck.theme; },
    };
  },
});
Deck.hide('blank-7');
