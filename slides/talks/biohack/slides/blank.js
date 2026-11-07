// Placeholder slides to fill in, after the outline: one per entry of SLIDES, as [section, heading, placeholder].
// Each shows its heading and a muted line saying what goes there; the section puts it in that part of the
// footer (outline.js names the sections). When a slide needs more than that, give it its own file in slides/
// (one module per slide, like title.js) and drop its entry here. One step each.
{
// TODO(final): each of these still says "Placeholder: ..." on screen; give it real content (its own file) or
// delete it. 'blank-7' (Demo) is hidden by demo.js.
const SLIDES = [
  ['1', 'Deciding what to test next is hard',
    'Knowledge is scattered across papers, databases and protocols; choosing the next experiment still rests on expert intuition.'],
  ['2', 'A knowledge graph of biology',
    'Genes, proteins, pathways, diseases and drugs, from an existing graph (e.g. PrimeKG, UniProt).'],
  ['2', 'A knowledge graph of experiments',
    'System → perturbation → assay → readout, built from published protocols and linked to the biology graph.'],
  ['2', 'Asking in plain language',
    'An LLM retrieves from both graphs and proposes the next experiment, citing what it used.'],
  ['3', 'A retrospective benchmark',
    'From paper N, predict the experiment of its follow-up paper N+1, then score the proposals against what was actually done.'],
  ['4', 'Results',
    'Graph retrieval vs. plain RAG vs. no retrieval.'],
  ['5', 'Demo',
    'A live query, from question to proposed experiment.'],
  ['6', 'Closing the loop',
    'Feed lab results back into the graphs, so each round of experiments improves the next suggestion.'],
];

SLIDES.forEach(([section, heading, placeholder], i) => {
  Deck.section(section);
  Deck.slide(`blank-${i + 1}`, {
    notes: '',
    mount(frame, { esc }) {
      frame.innerHTML = `<h2 class="deck-heading reveal-in" data-from="1">${esc(heading)}</h2>
        <p class="deck-lead deck-muted reveal-in" data-from="1" style="--i:1">Placeholder: ${esc(placeholder)}</p>`;
      return { enter: (step, animate) => Deck.show(frame, step, animate) };
    },
  });
});
Deck.section(null);
}
