"""Validate blinded grade structure, exact evidence quotes, provenance and arithmetic.
No LLM calls; can validate partial batches. python -m benchmark.judge.validate [--complete]
"""
import argparse,hashlib,json,math,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
AXES=('suitability','procedural_soundness','numerical_soundness')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(packet,grade):
    errors=[]
    if grade.get('item_id')!=packet['item_id']:errors.append('item ID mismatch')
    if grade.get('rubric_version')!='v1':errors.append('rubric version mismatch')
    axes=grade.get('axes',{})
    if set(axes)!=set(AXES):errors.append('axis keys mismatch')
    for name in AXES:
        a=axes.get(name,{})
        if type(a.get('score')) is not int or a['score'] not in (0,1,2):errors.append(name+': invalid score')
        if not isinstance(a.get('rationale'),str) or not a['rationale'].strip():errors.append(name+': missing rationale')
        quotes=a.get('response_quotes',[])
        if not isinstance(quotes,list) or not quotes or any(not isinstance(q,str) or not q.strip() or q not in packet['response_text'] for q in quotes):errors.append(name+': nonliteral or missing quote')
        if a.get('confidence') not in ('high','medium','low'):errors.append(name+': invalid confidence')
        paths=a.get('input_evidence_paths',[])
        if not isinstance(paths,list):errors.append(name+': evidence paths must be a list');continue
        for path in paths:
            try:
                value=packet
                for part in re.sub(r'\[(\d+)\]', r'.\1', path).split('.'):
                    value=value[int(part)] if isinstance(value,list) else value[part]
            except (KeyError,ValueError,IndexError,TypeError,AttributeError):errors.append(name+': invalid evidence path '+str(path))
    failures=grade.get('critical_failures')
    if not isinstance(failures,list):errors.append('critical_failures must be list')
    else:
        for fail in failures:
            if not isinstance(fail,dict) or fail.get('axis') not in AXES or not fail.get('issue') or not fail.get('reason') or not fail.get('response_quote') or fail['response_quote'] not in packet['response_text']:errors.append('invalid critical failure evidence')
    if not isinstance(grade.get('not_assessable_components'),list):errors.append('missing not-assessable components')
    for field in ('assumption_handling','review_reason'):
        if not isinstance(grade.get(field),str) or not grade[field].strip():errors.append('missing '+field)
    if type(grade.get('needs_human_review')) is not bool:errors.append('missing review boolean')
    numeric=grade.get('numeric_check',{})
    if set(numeric)!={'top_uM','factor','points','computed_min_uM','prose_consistent','notes'}:errors.append('numeric_check schema mismatch')
    if numeric.get('prose_consistent') not in (True,False,None):errors.append('invalid prose consistency')
    t,f,n=numeric.get('top_uM'),numeric.get('factor'),numeric.get('points')
    if all(type(x) in (int,float) for x in (t,f,n)) and t>0 and f>1 and int(n)==n and n>=2:
        try:
            expected=t/f**(n-1);reported=numeric.get('computed_min_uM')
            if not isinstance(reported,(int,float)) or not math.isclose(expected,reported,rel_tol=.02,abs_tol=1e-12):errors.append('judge minimum arithmetic mismatch')
        except OverflowError:errors.append('judge numeric overflow')
    return errors

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--complete',action='store_true');args=ap.parse_args()
    m=json.loads((OUT/'manifest.json').read_text());assert sha(OUT/'PROMPT.md')==m['prompt_sha256'],'Prompt changed after freeze'
    report={'checked':0,'missing':[],'errors':{},'grade_hashes':{}}
    for j in m['jobs']:
        key=j['item_id'];p=OUT/'packets'/f'{key}.json';assert sha(p)==j['packet_sha256']
        g=OUT/'grades'/f'{key}.json'
        if not g.exists():report['missing'].append(key);continue
        try:errors=validate(json.loads(p.read_text()),json.loads(g.read_text()))
        except (ValueError,TypeError,AttributeError) as e:errors=[type(e).__name__]
        if errors:report['errors'][key]=errors
        report['checked']+=1;report['grade_hashes'][key]=sha(g)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'checked':report['checked'],'missing':len(report['missing']),'errors':report['errors']}))
    if report['errors'] or (args.complete and report['missing']):raise SystemExit(1)
if __name__=='__main__':main()
