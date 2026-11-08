"""Offline checks for four-model pilot; no API usage or scientific validation."""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'benchmark/runs/four-model-pilot'


def main():
 manifest=json.loads((RUN/'manifest.json').read_text());results=[]
 for record in manifest['requests']:
  folder=RUN/record['slug'];cid=record['case_id'];raw=(folder/f'{cid}.input.json').read_bytes()
  assert hashlib.sha256(raw).hexdigest()==record['input_sha256']
  assert raw==(ROOT/f'benchmark/runs/gpt-oss-120b-pilot/{cid}.input.json').read_bytes()
  inp=json.loads(raw);out=json.loads((folder/f'{cid}.output.json').read_text())
  reference=json.loads((ROOT/f'slides/talks/biohack/graph/cases/{cid}.review.json').read_text())
  assert all(x not in raw.decode() for x in reference['audit']['excluded_documents']+reference['audit']['excluded_assays'])
  cards={c['id']:c for c in inp['step_cards']};used=[s.get('card_id') for s in out.get('steps',[])]
  errors=[f'{c} requires {req} earlier' for i,c in enumerate(used) for req in cards.get(c,{}).get('requires',[]) if req not in used[:i]]
  allowed=set(re.findall(r'CHEMBL\d+|Q\w{5}|proto:[a-z_]+',raw.decode()))|set(cards)
  citations=out.get('citations',[])
  t,f,n,r=[out.get(k) for k in ['top_concentration_uM','dilution_factor','n_points','replicates']]
  valid=type(t) in (int,float) and math.isfinite(t) and t>0 and type(f) in (int,float) and math.isfinite(f) and f>1 and type(n) is int and n>=2 and type(r) is int and r>0
  series=[1000*t/f**i for i in range(n)] if valid else []
  truth=reference['answer']['reference_measurement']['ic50_nM']
  results.append({'model':record['model'],'case_id':cid,'all_contract_fields_present':set(inp['output_contract'])<=out.keys(),'input_matches_previous_pilot':True,'source_exclusion_check':True,'valid_numeric_series':valid,'series_nM':series,'reference_ic50_nM':truth,'points_below':sum(x<truth for x in series),'points_above':sum(x>truth for x in series),'brackets_reference':min(series)<=truth<=max(series) if series else None,'two_each_side':sum(x<truth for x in series)>=2 and sum(x>truth for x in series)>=2 if series else None,'log10_span':math.log10(max(series)/min(series)) if series else None,'unknown_step_cards':[c for c in used if c not in cards],'prerequisite_errors':errors,'non_exact_citations':[c for c in citations if c not in allowed],'assay_comparability':'Not established; diagnostic only. Internal prose/parameter contradictions require manual review.'})
 (RUN/'diagnostics.json').write_text(json.dumps(results,indent=2)+'\n')
 for row in results:print(row['model'],row['case_id'],'brackets',row['brackets_reference'],'below/above',row['points_below'],row['points_above'],'citation format issues',len(row['non_exact_citations']))


if __name__=='__main__':main()
