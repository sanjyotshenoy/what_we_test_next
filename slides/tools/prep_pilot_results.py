"""Export recorded pilot grades and provider usage for the presentation.
Run from repository root: python -m slides.tools.prep_pilot_results
No inference calls. Scores remain provisional Codex judgments.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'benchmark/runs'
OUT=ROOT/'slides/talks/biohack/data'
NAMES={'moonshotai/Kimi-K3.1-Pro':'Kimi K3.1 Pro','zai-org/GLM-5.3':'GLM 5.3','deepseek-ai/DeepSeek-V4.1-Flash-1017':'DeepSeek V4.1 Flash','nvidia/nemotron-3-super-120b-a12b':'Nemotron 3 Super','openai/gpt-oss-120b':'GPT-OSS-120B'}


def main():
 grades=json.loads((BASE/'four-model-pilot/provisional_grades.json').read_text())['grades']
 old=(BASE/'gpt-oss-120b-pilot/RESULTS.md').read_text()
 rows=re.findall(r'^\| ([123]) \| ([012]) \| ([012]) \| ([012]) \|',old,re.M)
 assert len(rows)==3
 grades += [{'model':'openai/gpt-oss-120b','case_id':f'case-{i}','suitability':int(s),'steps':int(p),'numerical_soundness':int(n)} for i,s,p,n in rows]
 requests=[]
 for folder in ['gpt-oss-120b-pilot','four-model-pilot']:
  m=json.loads((BASE/folder/'manifest.json').read_text())
  requests += [dict(r,model=r.get('model',m.get('model'))) for r in m['requests']]
 models=[]
 for mid,name in NAMES.items():
  g=[r for r in grades if r['model']==mid];rs=[r for r in requests if r['model']==mid]
  assert len(g)==len(rs)==3
  axes={k:sum(r[k] for r in g) for k in ['suitability','steps','numerical_soundness']}
  models.append({'id':mid,'name':name,'axes':axes,'total':sum(axes.values()),'maximum':18,'input_tokens':sum(r['usage']['prompt_tokens'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs),'estimated_usd':sum(r['estimated_cost_usd'] for r in rs)})
 payload={'models':models,'cases_per_model':3,'responses_per_case':1,'grader':'Provisional Codex review; uncalibrated, not expert-validated','method':'Fixed isolated input packets; same requested settings; no tools or retrieval during generation','total_tokens':sum(m['input_tokens']+m['output_tokens'] for m in models),'estimated_total_usd':sum(m['estimated_usd'] for m in models),'sources':['benchmark/runs/four-model-pilot/provisional_grades.json','benchmark/runs/four-model-pilot/manifest.json','benchmark/runs/gpt-oss-120b-pilot/RESULTS.md','benchmark/runs/gpt-oss-120b-pilot/manifest.json']}
 assert payload['total_tokens']==52155
 assert [m['total'] for m in models]==[14,12,11,10,10]
 OUT.mkdir(exist_ok=True)
 text=json.dumps(payload,indent=2)+'\n'
 (OUT/'pilot_results.json').write_text(text)
 (OUT/'pilot_results.js').write_text('window.DATA=window.DATA||{};window.DATA.pilotResults='+text.strip()+';\n')
 print('Exported five models; totals and token counts verified.')


if __name__=='__main__':main()
