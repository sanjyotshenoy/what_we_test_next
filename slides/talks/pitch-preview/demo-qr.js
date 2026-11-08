// One step: invite the audience to open the demo on their phones.
Deck.slide('demo-qr', {
 notes: 'Invite the audience to scan the QR code and try the demo on a phone. The code links to https://demo-o10eetwuq.gobrev.dev. Backup slides follow.',
 mount(frame, {css}) {
  css(`.deck-frame .dq-title{left:4.2%;right:4.2%;text-align:center}.dq-intro{position:absolute;left:10%;right:10%;top:17%;text-align:center;font-size:var(--t-body);color:var(--muted)}.deck-frame a.dq-code{position:absolute;left:34.5%;top:29%;width:31%;height:55.11%;display:block;aspect-ratio:1;background:white;padding:.7%;box-sizing:border-box}.deck-frame a.dq-code img{display:block;width:100%;height:100%;object-fit:contain}.dq-link{position:absolute;left:10%;right:10%;top:87%;text-align:center;font-size:var(--t-caption)}.dq-link a{color:var(--accent)}`);
  frame.innerHTML = `<h2 class="deck-heading dq-title">Try the demo</h2><p class="dq-intro">Scan to explore — works on your phone, too.</p><a class="dq-code" href="https://demo-o10eetwuq.gobrev.dev" target="_blank" rel="noopener"><img src="assets/demo-qr.png" alt="QR code to open the demo"></a><p class="dq-link"><a href="https://demo-o10eetwuq.gobrev.dev" target="_blank" rel="noopener">demo-o10eetwuq.gobrev.dev ↗</a></p>`;
  return {enter(){}};
 }
});
