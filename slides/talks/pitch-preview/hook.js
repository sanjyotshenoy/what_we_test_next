// Four beats: centered neutral plate; color/label and shift left; proposed inhibition; experiment question.
// TODO(final): schematic hypothesis animation; the grey pathogen represents proposed inhibition, not an observed outcome.
{
Deck.slide('pitch-hook', {steps:4,
 notes:'0:00–0:50. Step 1: show only the title and a centered neutral bacterial plate. Step 2: introduce a microbiome researcher with a candidate compound and selected strains. Explain that activity against the pathogen alone is not enough: the experiment must also measure the effect on commensals. Color the pathogen and commensals, reveal the labels and move the plate left. Step 3: reveal compound X and the question, draw a T-ended inhibitory connection to the pathogen, then grey it out. This visualizes the hypothesized selective effect, not measured inhibition or survival; keep the spoken framing as a question. Step 4: ask what experiment would answer it, then advance to the missing-link graph. Compound discovery and strain selection are upstream. We support turning a supplied research question into a justified experiment. No clinical or wet-lab outcome is claimed.',
 mount(frame,{css}) {
 css(`
 .ph-scene{position:absolute;left:28.5%;top:19%;width:43%;height:61%;transition:left .8s ease-in-out;}
 .ph-labeled .ph-scene{left:5%;}
 .ph-scene svg{width:100%;height:100%;overflow:visible;}
 .ph-boundary{fill:var(--muted);fill-opacity:.035;stroke:var(--detail);stroke-width:2;}
 .ph-cell{fill:var(--muted);fill-opacity:.16;stroke:var(--muted);stroke-width:3;transition:fill .4s,stroke .4s;}
 .ph-labeled .ph-cell{fill:var(--accent);stroke:var(--accent);}
 .ph-labeled .ph-pathogen{fill:var(--plot-2);stroke:var(--plot-2);}
 .ph-proposed .ph-pathogen{fill:var(--muted);stroke:var(--muted);}
 .ph-motion.ph-proposed .ph-pathogen{transition-delay:1s;}
 .ph-compound{opacity:0;transform:translateY(-12px);transition:opacity .3s,transform .3s;}
 .ph-proposed .ph-compound{opacity:1;transform:translateY(0);}
 .ph-compound circle{fill:var(--bg);stroke:var(--fg);stroke-width:2;}
 .ph-compound text{fill:var(--fg);font-family:Lato,sans-serif;font-size:var(--t-caption);text-anchor:middle;dominant-baseline:middle;}
 .ph-inhibit{fill:none;stroke:var(--plot-2);stroke-width:3;stroke-dasharray:1;stroke-dashoffset:1;opacity:0;transition:stroke-dashoffset .65s ease,opacity .15s;}
 .ph-proposed .ph-inhibit{stroke-dashoffset:0;opacity:1;}
 .ph-motion.ph-proposed .ph-inhibit{transition-delay:.3s;}
 .ph-stop{stroke:var(--plot-2);stroke-width:3;opacity:0;transition:opacity .15s;}
 .ph-proposed .ph-stop{opacity:1;}
 .ph-motion.ph-proposed .ph-stop{transition-delay:.9s;}
 .ph-legend{position:absolute;left:8%;right:8%;bottom:-3%;display:flex;justify-content:center;gap:1.3em;font-size:var(--t-small);opacity:0;transition:opacity .4s;}
 .ph-labeled .ph-legend{opacity:1;}
 .ph-legend span{white-space:nowrap;}
 .ph-legend i{display:inline-block;width:.65em;height:.65em;border-radius:50%;margin-right:.35em;background:var(--accent);}
 .ph-legend .ph-pkey{background:var(--plot-2);}
 .ph-user{position:absolute;left:53%;right:5%;top:21%;font-size:var(--t-small);color:var(--muted);line-height:1.35;}
 .ph-copy{position:absolute;left:53%;right:5%;top:32%;font-size:var(--t-lead);line-height:1.35;}
 .ph-copy p{margin:0;}
 .ph-copy strong{color:var(--accent);}
 .ph-experiment{position:absolute;left:53%;right:5%;top:60%;font-size:var(--t-lead);line-height:1.3;}
 .ph-experiment strong{color:var(--accent);}
 .ph-experiment small{display:block;margin-top:.75em;font-size:var(--t-small);color:var(--muted);}
 .ph-jump .ph-scene,.ph-jump .ph-cell,.ph-jump .ph-compound,.ph-jump .ph-inhibit,.ph-jump .ph-stop,.ph-jump .ph-legend{transition:none!important;}
 `);
 const cells=[
  {x:166,y:183,r:25,pathogen:true},
  {x:250,y:132,r:20},{x:326,y:179,r:23},{x:300,y:257,r:19},
  {x:216,y:292,r:23},{x:132,y:261,r:18},{x:233,y:218,r:16},
 ];
 const blobs=cells.map((c,i)=>`<g transform="translate(${c.x} ${c.y}) rotate(${i*29})"><path class="ph-cell ${c.pathogen?'ph-pathogen':''}" d="M ${-c.r} 0 C ${-c.r-7} ${-c.r}, ${c.r-4} ${-c.r-9}, ${c.r} -3 C ${c.r+8} ${c.r+2}, ${-c.r+3} ${c.r+8}, ${-c.r} 0 Z"/></g>`).join('');
 frame.innerHTML=`<h2 class="deck-heading">Inhibit the pathogen. Spare the commensals?</h2>
 <div class="ph-scene"><svg viewBox="0 0 460 390" role="img" aria-label="Schematic hypothesis: compound X may inhibit a pathogen while sparing commensals. Not an observed result."><circle class="ph-boundary" cx="230" cy="213" r="159"/>${blobs}<g class="ph-compound"><circle cx="230" cy="20" r="23"/><text x="230" y="21">X</text></g><path class="ph-inhibit" pathLength="1" d="M230 46 Q166 70 166 142"/><path class="ph-stop" d="M153 142 L179 142"/></svg><div class="ph-legend"><span><i class="ph-pkey"></i>Pathogen</span><span><i></i>Commensals</span></div></div>
 <div class="ph-user reveal-in" data-from="2">For a microbiome researcher:<br>a candidate compound, selected strains.</div>
 <div class="ph-copy"><p class="ph-question reveal-in" data-from="3">Will <strong>compound X</strong> inhibit the pathogen while sparing these commensals?</p></div>
 <div class="ph-experiment reveal-in" data-from="4"><strong>What experiment<br>would answer this?</strong><small>Measure the effect on the pathogen<br>and on the commensals.</small></div>`;
 return{enter:(s,a)=>{frame.classList.toggle('ph-jump',!a);frame.classList.toggle('ph-motion',Boolean(a));frame.classList.toggle('ph-labeled',s>=2);frame.classList.toggle('ph-proposed',s>=3);Deck.show(frame,s,a);if(a && s===3)return new Promise(resolve=>setTimeout(resolve,1500));}};
 }});
}
