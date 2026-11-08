"""Offline audit, packet preparation and summary for the Astra-medium extension.
Execution uses fresh collaboration agents; this module makes no model/API calls.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from .judge.validate import validate, AXES

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'benchmark/runs/astra-medium-20'
JUDGE = ROOT/'benchmark/judge_extension_v1'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def write(path, obj): path.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')
def now(): return datetime.now(timezone.utc).isoformat()

def reconcile():
    m=read(RUN/'manifest.json')
    assert sha(RUN/'GENERATION_PROMPT.txt')==m['system_prompt_sha256']
    for r in m['requests']:
        cid=r['case_id']; assert sha(RUN/'inputs'/f'{cid}.json')==r['input_sha256']
        out=RUN/'outputs'/f'{cid}.output.txt'
        if r['status']=='completed':
            assert sha(out)==r['output_sha256'], 'Saved output changed'
        if out.exists() and r['status']=='started':
            raw=out.read_text()
            try:
                parsed=json.loads(raw); valid=isinstance(parsed,dict)
            except ValueError:valid=False
            r.update(status='completed',finished_utc=now(),output_sha256=sha(out),valid_json=valid,output_characters=len(raw),output_whitespace_words=len(raw.split()),provider_tokens=None)
    write(RUN/'manifest.json',m)
    return m

def prepare():
    m=reconcile();assert all(r['status']=='completed' for r in m['requests'])
    assert not (JUDGE/'manifest.json').exists(), 'Do not overwrite frozen judge packets'
    jobs=[];mapping={}
    for r in m['requests']:
        cid=r['case_id'];key=hashlib.sha256(('astra-extension-v1:'+cid).encode()).hexdigest()[:16]
        review=read(ROOT/f'slides/talks/biohack/graph/cases/{cid}.review.json')
        packet={'item_id':key,'generator_input':read(RUN/'inputs'/f'{cid}.json'),'reviewer_only_context':{'expected_endpoint':review['answer']['expected_endpoint'],'procedure_expectation':review['answer']['procedure_expectation'],'limitations':review['answer'].get('review_limitations',[]),'note':'Incomplete reference; not a unique correct protocol. Hidden potency and coverage are deliberately omitted.'},'response_text':(RUN/'outputs'/f'{cid}.output.txt').read_text()}
        p=JUDGE/'packets'/f'{key}.json';write(p,packet);jobs.append({'item_id':key,'packet_sha256':sha(p),'status':'pending'});mapping[key]=cid
    import random
    random.Random(20261108).shuffle(jobs)
    write(JUDGE/'mapping.json',mapping)
    write(JUDGE/'manifest.json',{'judge':'gpt-6-astra','reasoning_effort':'medium','prompt_sha256':sha(JUDGE/'PROMPT.md'),'jobs':jobs})

def judge_reconcile():
    m=read(JUDGE/'manifest.json');assert sha(JUDGE/'PROMPT.md')==m['prompt_sha256']
    assert m['prompt_sha256']==sha(ROOT/'benchmark/judge/PROMPT.md')
    for j in m['jobs']:
        key=j['item_id'];p=JUDGE/'packets'/f'{key}.json';assert sha(p)==j['packet_sha256'];g=JUDGE/'grades'/f'{key}.json'
        if g.exists():
            errors=validate(read(p),read(g));assert not errors,(key,errors)
            if j['status']!='completed':j.update(status='completed',finished_utc=now(),grade_sha256=sha(g))
            else:assert sha(g)==j['grade_sha256']
    write(JUDGE/'manifest.json',m)
    return m

def summarize():
    m=reconcile();jm=judge_reconcile();assert len(jm['jobs'])==20 and all(j['status']=='completed' for j in jm['jobs'])
    mapping=read(JUDGE/'mapping.json');rows=[]
    for j in jm['jobs']:
        key=j['item_id'];g=read(JUDGE/'grades'/f'{key}.json');scores={a:g['axes'][a]['score'] for a in AXES}
        rows.append({'case_id':mapping[key],'item_id':key,'scores':scores,'total':sum(scores.values()),'critical_failures':len(g['critical_failures']),'grade_file':f'../../judge_extension_v1/grades/{key}.json'})
    rows.sort(key=lambda r:int(r['case_id'].split('-')[1]))
    summary={'model':'Astra medium','n':20,'axis_means':{a:sum(r['scores'][a] for r in rows)/20 for a in AXES},'mean_total_out_of_6':sum(r['total'] for r in rows)/20,'cases_with_critical_failure':sum(bool(r['critical_failures']) for r in rows)}
    write(RUN/'results.json',{'summary':summary,'grades':rows,'status':'Provisional same-model AI judging; different transport and reasoning effort from prior candidates'})
    old=read(ROOT/'benchmark/judge/results.json')['summary']
    lines=['# Astra medium: 20-case benchmark extension','','**Provisional AI judgments, not expert validation. Astra both generated and judged this extension in separate fresh contexts; same-model preference bias is possible.**','','## Scores','','All 20 responses scored 2 for suitability and 1 for procedural soundness. Numerical soundness was 2 in cases 1 and 12 and 1 in the other 18. The judge treated these as coherent but incomplete proposals, with unresolved operating conditions and frequent numerical abstention; zero flagged critical failures does not mean executable or validated protocols.','','| Candidate | Suitability /2 | Procedure /2 | Numbers /2 | Mean total /6 | Cases with critical failure |','|---|---:|---:|---:|---:|---:|']
    for r in [summary]+old:
        a=r['axis_means'];lines.append(f"| {r['model']} | {a['suitability']:.2f} | {a['procedural_soundness']:.2f} | {a['numerical_soundness']:.2f} | {r['mean_total_out_of_6']:.2f} | {r['cases_with_critical_failure']}/20 |")
    lines+=['','## Exact design and comparison limits','','- Same 20 input packet bytes and generation instruction as the existing five-model run. Input hashes, execution agent IDs and raw output hashes are in [manifest.json](manifest.json). One response per case; no output repair, retries or selection.','- Fresh `gpt-6-astra` generator at **medium** reasoning per case, with no inherited conversation, judge rubric, reviewer answers or other responses. File tools only transport the input and final output; browsing and retrieval are prohibited.','- Prior candidates ran through Nebius at low reasoning, temperature 0, JSON mode and an 8192-token cap. The collaboration interface cannot match/enforce those settings and adds its own system/tool scaffolding. This is a controlled-context extension, not an identical-serving-settings model comparison.','- A different fresh Astra-medium judge scores each response using the exact original frozen v1 rubric and incomplete endpoint guidance. Model names, prior scores and hidden potency are withheld; identity may still be inferred from style. Same-model bias is not eliminated by fresh contexts.','- The original four synthetic rubric-anchor checks remain applicable because the rubric is unchanged. They do not establish expert agreement. There is no repeated-judge variance estimate, independent judge-family review or wet-lab validation.','- All grade JSON passes literal-quote, evidence-path, schema and arithmetic checks. That does not establish scientific correctness. Unknown lab conditions and assay compatibility remain not assessable.','- Equal-weight totals are descriptive. Critical failures must not be averaged into a passing result. The 20 purposive cases are not a representative independent sample.','','## Usage','','20 generation tasks and 20 judge tasks through Codex collaboration. **No Nebius API calls. Provider token counts and billing are unavailable**, not zero. Output character and whitespace-word counts are stored as text size diagnostics, never as token receipts. The $100 Nebius credit balance was not queried or changed by this workflow.','','## Per-case evidence','','| Case | Suitability | Procedure | Numbers | Total /6 | Critical failures | Judge rationale |','|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        a=r['scores'];lines.append(f"| {r['case_id']} | {a['suitability']} | {a['procedural_soundness']} | {a['numerical_soundness']} | {r['total']} | {r['critical_failures']} | [evidence]({r['grade_file']}) |")
    lines+=['','## Reproduce offline','','Run `python -m benchmark.astra_medium --summarize`. This validates and aggregates saved artifacts without inference. Generation and grading require fresh isolated collaboration agents as recorded in the manifests. Historical comparison: [original five-model review](../../judge/RESULTS.md).','']
    (RUN/'RESULTS.md').write_text('\n'.join(lines));print(json.dumps(summary))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['generation','judge'],default='generation');ap.add_argument('--start',nargs=2,metavar=('ID','AGENT'));ap.add_argument('--next',type=int,default=0);ap.add_argument('--prepare-judge',action='store_true');ap.add_argument('--summarize',action='store_true');args=ap.parse_args()
    if args.prepare_judge:prepare();return
    if args.summarize:summarize();return
    m=reconcile() if args.phase=='generation' else judge_reconcile();rows=m['requests'] if args.phase=='generation' else m['jobs'];key='case_id' if args.phase=='generation' else 'item_id'
    if args.start:
        r=next(r for r in rows if r[key]==args.start[0]);assert r['status']=='pending';r.update(status='started',agent_id=args.start[1],model='gpt-6-astra',reasoning_effort='medium',fork_turns='none',started_utc=now());write((RUN if args.phase=='generation' else JUDGE)/'manifest.json',m)
    print('completed',sum(r['status']=='completed' for r in rows),'active',[r[key] for r in rows if r['status']=='started'])
    if args.next:print('next',[r[key] for r in rows if r['status']=='pending'][:args.next])
if __name__=='__main__':main()
