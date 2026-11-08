// One review slide: researcher input, interpreted goal, explicit missing-answer premise.
// TODO(final): replace the illustrative query with a reviewed demo query before claiming a recorded run.
{
Deck.slide('researcher-question',{
 steps:3,
 notes:'Scope agreed in discussion: the researcher supplies the compound, bacterial strains and research query. Candidate ranking and strain selection are upstream. Lab context is already available in the repo. This is an illustrative input, not a recorded model response or an actual database search. For this demo we assume an up-to-date KB lacks the answer to a genuinely new question; establishing novelty via meta-analysis is out of scope. An LLM may interpret the natural-language goal to guide assay/template retrieval. A MIC measurement is the example goal, not a claim that every query maps to MIC. Existing evidence would be returned to the researcher, who decides whether to repeat an experiment. Known incompatibility must block downstream compilation/hardware. This slide ends before template selection and parameterization.',
 mount(frame,{css}){
 css(`.rq-query{position:absolute;left:5%;top:19%;width:42%;font-size:var(--t-lead);line-height:1.4}.rq-query blockquote{margin:.6em 0;padding-left:.7em;border-left:3px solid var(--accent)}.rq-label{font-size:var(--t-small);color:var(--accent);font-weight:700}.rq-inputs{font-size:var(--t-small);line-height:1.7;margin-top:1em}.rq-context{font-size:var(--t-caption);color:var(--muted);line-height:1.4}.rq-right{position:absolute;left:56%;right:5%;top:20%;font-size:var(--t-body);line-height:1.35}.rq-right h3{margin:0 0 .45em;font-size:var(--t-body);color:var(--accent)}.rq-right p{margin:.4em 0}.rq-goal{padding:0 0 .35em;border-bottom:1px solid var(--detail)}.rq-gap{margin-top:.5em}.rq-next{position:absolute;left:5%;right:5%;top:79%;font-size:var(--t-body);padding-top:.6em;border-top:1px solid var(--detail)}.rq-arrow{position:absolute;left:49%;top:35%;font-size:var(--t-heading);color:var(--accent)}.rq-caption{position:absolute;left:5%;right:5%;top:88%;font-size:var(--t-caption);color:var(--muted)}`);
 frame.innerHTML=`<h2 class="deck-heading">A researcher brings a new question</h2>
 <div class="rq-query"><div class="rq-label">RESEARCHER INPUT</div><blockquote>“At what concentrations does compound X inhibit growth of these bacterial strains?”</blockquote><div class="rq-inputs"><strong>Compound X</strong> + <strong>specified strains</strong><br>Selected by the researcher</div><p class="rq-context">Lab hardware, reagents and constraints<br>are available as context.</p></div>
 <div class="rq-arrow reveal-in" data-from="2">→</div>
 <div class="rq-right"><div class="rq-goal reveal-in" data-from="2"><h3>1 · Interpret the question</h3><p>Measurement goal:<br><strong>MIC for each supplied strain</strong></p><p class="rq-context">The LLM translates the query into a goal that guides assay/template search.</p></div><div class="rq-gap reveal-in" data-from="3"><h3>2 · Check existing evidence</h3><p><strong>The answer is missing.</strong></p><p class="rq-context">Demo premise: an up-to-date KB,<br>with this question still unanswered.</p></div></div>
 <div class="rq-next reveal-in" data-from="3">Next: use established methods to design an experiment that answers this question.</div>
 <p class="rq-caption">Review prototype · illustrative query, not a recorded run · compound and strain selection stay upstream</p>`;
 return{enter:(s,a)=>Deck.show(frame,s,a)};
 }
});
}
