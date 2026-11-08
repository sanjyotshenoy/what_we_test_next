"""Prepare blinded single-response jobs, separate mapping, and frozen hashes. No model calls."""
import hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
RUN=ROOT/'benchmark/runs/twenty-case-pilot'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 items=[]
 for r in json.loads((RUN/'manifest.json').read_text())['requests']:
  folder=RUN/r['slug'];cid=r['case_id'];raw=(folder/f'{cid}.output.txt').read_text()
  inp=json.loads((folder/f'{cid}.input.json').read_text())
  review=json.loads((ROOT/f'slides/talks/biohack/graph/cases/{cid}.review.json').read_text())
  key=sha((r['slug']+':'+cid+':judge-v1').encode())[:16]
  item={'item_id':key,'generator_input':inp,'reviewer_only_context':{'expected_endpoint':review['answer']['expected_endpoint'],'procedure_expectation':review['answer']['procedure_expectation'],'limitations':review['answer'].get('review_limitations',[]),'note':'Incomplete reference; not a unique correct protocol. Hidden potency and coverage are deliberately omitted.'},'response_text':raw}
  items.append((key,item,{'model':r['slug'],'case_id':cid,'output_sha256':sha(raw.encode()),'input_sha256':r['input_sha256']}))
 random.Random(20261108).shuffle(items)
 for name in ('packets','grades','private'): (OUT/name).mkdir(exist_ok=True)
 mapping={};jobs=[]
 for key,item,meta in items:
  packet=json.dumps(item,indent=2,ensure_ascii=False)+'\n';(OUT/'packets'/f'{key}.json').write_text(packet)
  mapping[key]=meta;jobs.append({'item_id':key,'packet_sha256':sha(packet.encode())})
 (OUT/'private/mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
 manifest={'rubric_version':'v1','prompt_sha256':sha((OUT/'PROMPT.md').read_bytes()),'requested_judge':'gpt-6-astra','reasoning_effort':'medium','job_count':len(jobs),'isolation':'Fresh fork_turns=none subagent per response; only prompt and assigned packet allowed.','grading_usage':'Codex collaboration model execution, not Nebius. Provider token/billing receipts unavailable through this interface; do not claim zero compute cost.','jobs':jobs}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('Prepared',len(jobs),'blinded jobs; prompt hash',manifest['prompt_sha256'])
if __name__=='__main__':main()
