// One interactive slide: the real graph and pilot case viewer; no simulated agent run.
Deck.section(5);
Deck.slide('evidence-explorer', {
  before:'evidence-next', interactive:true,
  notes:'Open the graph viewer and inspect a measurement, its source and the case input/review split. This is a view of committed data and diagnostic cases, not a live agent or a benchmark result. The viewer has its own dataset controls.',
  mount(frame,{css}) {
    css(`.ex-frame {position:absolute;left:4.2%;top:18%;width:91.6%;height:65%;border:1px solid var(--detail);} .ex-link {color:var(--accent);}`);
    frame.innerHTML='<h2 class="deck-heading">Inspect the evidence behind a decision</h2><iframe class="ex-frame" src="graph/index.html" title="Repository graph and diagnostic case explorer"></iframe><p class="deck-caption"><a class="ex-link" href="graph/index.html" target="_blank" rel="noopener">Open graph explorer and case packets ↗</a> · committed data, not a live agent run</p>';
    return {enter(){}};
  }
});
Deck.section(null);
