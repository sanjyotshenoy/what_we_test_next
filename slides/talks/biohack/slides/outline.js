// The talk's sections, the footer along the bottom of every slide, and the outline slide. A dummy outline to
// fill in: change OUTLINE (and FOOTER) here, and the placeholder slides in blank.js to match.
//
// OUTLINE is the single list of sections: the outline slide shows it, and Deck.sections() puts it in the
// footer (FOOTER gives shorter footer names where a heading is long). Steps: the heading, then one section
// per click.
{
// TODO(final): confirm the sections against the finished talk (this is the dummy outline).
const OUTLINE = [
  ['1', 'The problem: what should we test next?'],
  ['2', 'Our approach: knowledge graphs + an LLM', [
    ['2.1', 'A knowledge graph of biology'],
    ['2.2', 'A knowledge graph of experiments'],
  ]],
  ['3', 'Evaluation: predicting the next experiment from past papers'],
  ['4', 'Results'],
  ['5', 'Live demo'],
  ['6', 'Closing the loop with the lab'],
];

const FOOTER = { 1: 'Problem', 2: 'Approach', 3: 'Evaluation', 4: 'Results', 5: 'Live demo', 6: 'Next steps' };
Deck.sections(OUTLINE.map(([num, heading]) => [num, FOOTER[num] || heading]));

Deck.slide('outline', {
  steps: 1 + OUTLINE.length,
  notes: 'The outline: one section per click.',
  mount(frame, { css, esc }) {
    css(`
      .o-list { position: absolute; left: 6.5%; top: 20%; }
      .o-group { margin-bottom: 1.1em; }
      .o-row { display: flex; align-items: baseline; font-size: var(--t-lead); }
      .o-num { width: 1.45em; font-weight: 700; color: var(--accent); }
      .o-sub { display: flex; align-items: baseline; font-size: var(--t-small); color: var(--muted);
        margin: .2em 0 0 2em; }
      .o-sub .o-num { width: 2em; font-weight: 400; color: var(--muted); }
    `);
    // a section's sub-items stagger in just behind it (--i); step 1 is the heading alone
    frame.innerHTML = `<h2 class="deck-heading reveal-in" data-from="1">Outline</h2>
      <div class="o-list">${OUTLINE.map(([num, heading, subs = []], i) => `
        <div class="o-group">
          <div class="o-row reveal-in" data-from="${i + 2}"><span class="o-num">${esc(num)}</span>${esc(heading)}</div>
          ${subs.map(([n, h], j) => `<div class="o-sub reveal-in" data-from="${i + 2}" style="--i:${j + 1}">
            <span class="o-num">${esc(n)}</span>${esc(h)}</div>`).join('')}
        </div>`).join('')}</div>`;
    return { enter: (step, animate) => Deck.show(frame, step, animate) };
  },
});
}
