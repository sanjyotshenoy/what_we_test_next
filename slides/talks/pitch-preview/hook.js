// Three beats: community; researcher-supplied compound/question; the experiment-design gap.
// TODO(final): schematic community, not measured composition, a treatment simulation or a survival result.
{
Deck.slide('pitch-hook', {steps:3,
 notes:'0:00–0:50, with the visual setup taking 15–20 seconds. Step 1: a schematic community contains a pathogen and commensals; these labels refer to the supplied experimental context, not universal good/bad categories. Step 2: introduce compound X and the researcher-supplied question, highlighting both groups without changing any organism count or showing death, inhibition or survival. Step 3: stop the emphasis and ask what experiment would answer the question. Advance directly to the missing-link graph. Compound discovery, strain selection and hypothesis generation are upstream. We support turning that question into a justified experiment. No clinical, wet-lab or selectivity outcome is claimed. Team Zhang et al., Nucleate Pittsburgh BioHack 2026.',
 mount(frame,{css}) {
 css(`
 .ph-scene{position:absolute;left:5%;top:19%;width:43%;height:61%;}
 .ph-scene svg{width:100%;height:100%;overflow:visible;}
 .ph-boundary{fill:var(--accent);fill-opacity:.035;stroke:var(--detail);stroke-width:2;}
 .ph-cell{fill:var(--accent);fill-opacity:.16;stroke:var(--accent);stroke-width:3;}
 .ph-pathogen{fill:var(--plot-2);stroke:var(--plot-2);}
 .ph-halo{fill:none;stroke:var(--accent);stroke-width:2;stroke-dasharray:5 5;opacity:0;transition:opacity .45s;}
 .ph-halo.ph-pathogen{stroke:var(--plot-2);fill:none;}
 .ph-ask .ph-halo{opacity:.8;}
 .ph-compound{opacity:0;transform:translateY(-12px);transition:opacity .4s,transform .4s;}
 .ph-ask .ph-compound,.ph-gap .ph-compound{opacity:1;transform:translateY(0);}
 .ph-compound circle{fill:var(--bg);stroke:var(--fg);stroke-width:2;}
 .ph-compound text{fill:var(--fg);font-family:Lato,sans-serif;font-size:var(--t-caption);text-anchor:middle;dominant-baseline:middle;}
 .ph-compound path{fill:none;stroke:var(--muted);stroke-width:2;stroke-dasharray:4 5;}
 .ph-legend{position:absolute;left:8%;right:8%;bottom:-3%;display:flex;justify-content:center;gap:1.3em;font-size:var(--t-small);}
 .ph-legend span{white-space:nowrap;}
 .ph-legend i{display:inline-block;width:.65em;height:.65em;border-radius:50%;margin-right:.35em;background:var(--accent);}
 .ph-legend .ph-pkey{background:var(--plot-2);}
 .ph-copy{position:absolute;left:53%;right:5%;top:23%;font-size:var(--t-lead);line-height:1.35;}
 .ph-kicker{font-size:var(--t-small);color:var(--muted);margin:0 0 .9em;}
 .ph-copy p{margin:0 0 .65em;}
 .ph-copy strong{color:var(--accent);}
 .ph-question{font-size:var(--t-body);}
 .ph-experiment{position:absolute;left:53%;right:5%;top:60%;font-size:var(--t-lead);line-height:1.3;}
 .ph-experiment strong{color:var(--accent);}
 .ph-experiment small{display:block;margin-top:.75em;font-size:var(--t-small);color:var(--muted);}
 .ph-jump .ph-compound,.ph-jump .ph-halo{transition:none;}
 `);
 const cells=[
  {x:166,y:183,r:25,pathogen:true},
  {x:250,y:132,r:20},{x:326,y:179,r:23},{x:300,y:257,r:19},
  {x:216,y:292,r:23},{x:132,y:261,r:18},{x:233,y:218,r:16},
 ];
 const blobs=cells.map((c,i)=>`<g transform="translate(${c.x} ${c.y}) rotate(${i*29})"><circle class="ph-halo ${c.pathogen?'ph-pathogen':''}" r="${c.r+10}"/><path class="ph-cell ${c.pathogen?'ph-pathogen':''}" d="M ${-c.r} 0 C ${-c.r-7} ${-c.r}, ${c.r-4} ${-c.r-9}, ${c.r} -3 C ${c.r+8} ${c.r+2}, ${-c.r+3} ${c.r+8}, ${-c.r} 0 Z"/></g>`).join('');
 frame.innerHTML=`<h2 class="deck-heading">What should we test next?</h2>
 <div class="ph-scene"><svg viewBox="0 0 460 390" role="img" aria-label="Schematic community: one pathogen and six commensal blobs. No treatment outcomes shown."><circle class="ph-boundary" cx="230" cy="213" r="159"/>${blobs}<g class="ph-compound"><circle cx="230" cy="20" r="23"/><text x="230" y="21">X</text><path d="M230 46 L230 84"/></g></svg><div class="ph-legend"><span><i class="ph-pkey"></i>Pathogen</span><span><i></i>Commensals</span></div></div>
 <div class="ph-copy"><p class="ph-kicker">Researcher-supplied question</p><p class="reveal-in" data-from="1">A compound.<br>Specified bacterial strains.</p><p class="ph-question reveal-in" data-from="2">Will <strong>compound X</strong> inhibit the pathogen while sparing these commensals?</p></div>
 <div class="ph-experiment reveal-in" data-from="3"><strong>What experiment<br>would answer this?</strong><small>Turn a research question into a justified experiment.</small></div>
 <p class="deck-caption">Schematic community · outcomes unknown · compound discovery and strain selection are upstream</p>`;
 return{enter:(s,a)=>{frame.classList.toggle('ph-jump',!a);frame.classList.toggle('ph-ask',s===2);frame.classList.toggle('ph-gap',s>=3);Deck.show(frame,s,a);}};
 }});
}
