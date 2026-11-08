/* Reviewer-only cases. The input JSON is the entire permitted model context. */
'use strict';
{
  const el=(tag,text,parent)=>{const e=document.createElement(tag);if(text!==null)e.textContent=text;if(parent)parent.append(e);return e;};
  const pre=(data,parent)=>el('pre',JSON.stringify(data,null,2),parent);
  const tabs=[document.getElementById('graph-tab'),document.getElementById('cases-tab')];
  function activate(index){tabs.forEach((t,i)=>{t.setAttribute('aria-selected',String(i===index));t.tabIndex=i===index?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=i!==index;});history.replaceState(null,'',index?'#cases':'#graph');}
  tabs.forEach((t,i)=>{t.onclick=()=>activate(i);t.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?1:1-i;activate(n);tabs[n].focus();}};});
  if(location.hash==='#cases')activate(1);
  const host=document.getElementById('case-cards');
  for(const c of window.BENCHMARK_CASES){
    const article=el('article',null,host);article.className='case-card';
    el('p',`${c.id.toUpperCase()} · ${c.status}`,article).className='case-label';
    el('h2',c.title,article);
    el('h3','Question given to the model',article);el('p',c.input.question,article);
    el('h3','Why this case?',article);el('p',c.rationale,article);
    el('p',`${c.input.retained_measurement_examples.length} retained measurement examples · ${c.input.step_cards.length} parameterized step cards · no query-pair measurements in the input packet`,article).className='note';
    const links=el('p',null,article);const input=el('a','Download model input JSON',links);input.href=`cases/${c.id}.input.json`;input.download='';el('span',' · ',links);const review=el('a','Download reviewer record',links);review.href=`cases/${c.id}.review.json`;review.download='';
    const context=el('details',null,article);el('summary','Inspect exactly what the model receives',context);pre(c.input,context);
    const toggle=el('button','Show reference answer & split audit',article);toggle.className='answer-toggle';toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls',`${c.id}-answer`);
    const answer=el('section',null,article);answer.id=`${c.id}-answer`;answer.hidden=true;answer.className='case-answer';
    toggle.onclick=()=>{answer.hidden=!answer.hidden;toggle.setAttribute('aria-expanded',String(!answer.hidden));toggle.textContent=answer.hidden?'Show reference answer & split audit':'Hide reference answer & split audit';};
    el('h3','Held-out evidence—not a unique correct protocol',answer);
    el('p',`Recorded IC50: ${c.answer.reference_measurement.ic50_nM} nM (${c.answer.reference_measurement.ic50_nM/1000} µM). Assay: ${c.answer.assay.id}.`,answer);
    el('p',c.answer.assay.props.description,answer);el('p',c.answer.expected_endpoint,answer);el('p',c.answer.numerical_reference,answer);
    const doi=c.answer.document.doi;if(doi){const a=el('a',`Source: ${doi}`,answer);a.href=`https://doi.org/${encodeURI(doi)}`;a.target='_blank';a.rel='noopener noreferrer';}
    el('h3','Three-axis grading',answer);
    const list=el('ul',null,answer);
    el('li','Suitability: 0 = wrong endpoint/system; 1 = plausible but incomplete; 2 = directly addresses the question and limits its claims.',list);
    el('li','Steps: 0 = invalid or essential stages missing; 1 = coherent outline with unresolved details; 2 = supported, ordered procedure with controls and bound parameters.',list);
    el('li','Numerical soundness: 0 = invalid/incompatible; 1 = plausible but incompletely supported; 2 = justified, internally consistent values and manageable uncertainty. Unknown reference conditions stay unscored.',list);
    el('p','Report three scores separately, critical failures and uncertainty. Coverage of the held-out IC50 is a separate diagnostic, conditional on assay comparability; it is not an exact-match grade.',answer);
    const audit=el('details',null,answer);el('summary','Exact exclusions, counts and source hashes',audit);pre(c.audit,audit);
  }
}
