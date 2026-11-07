// Empty slides to fill in: one per entry of HEADINGS, after the title. Type a heading to give one a title;
// when a slide needs more than that, give it its own file in slides/ (one module per slide, like title.js) and
// drop its entry here. One step each.
{
const HEADINGS = ['', '', '', '', ''];

HEADINGS.forEach((heading, i) => Deck.slide(`blank-${i + 1}`, {
  notes: '',
  mount(frame, { esc }) {
    frame.innerHTML = heading ? `<h2 class="deck-heading reveal-in" data-from="1">${esc(heading)}</h2>` : '';
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
}));
}
