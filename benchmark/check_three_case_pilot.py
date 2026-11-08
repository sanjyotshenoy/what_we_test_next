"""Offline structural and series diagnostics; not a scientific validity grader.
Run: python -m benchmark.check_three_case_pilot
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'benchmark/runs/gpt-oss-120b-pilot'


def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    results=[]
    for record in manifest['requests']:
        cid=record['case_id']
        raw=(RUN/f'{cid}.input.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==record['input_sha256']
        inp=json.loads(raw)
        out=json.loads((RUN/f'{cid}.output.json').read_text())
        reference=json.loads((ROOT/f'slides/talks/biohack/graph/cases/{cid}.review.json').read_text())
        assert all(x not in raw.decode() for x in reference['audit']['excluded_documents']+reference['audit']['excluded_assays'])
        t,f,n,r=(out.get(k) for k in ['top_concentration_uM','dilution_factor','n_points','replicates'])
        valid=isinstance(t,(float,int)) and math.isfinite(t) and t>0 and isinstance(f,(float,int)) and math.isfinite(f) and f>1 and type(n) is int and n>=2 and type(r) is int and r>0
        series=[1000*t/f**i for i in range(n)] if valid else []
        truth=reference['answer']['reference_measurement']['ic50_nM']
        cards={c['id']:c for c in inp['step_cards']}
        used=[s.get('card_id') for s in out.get('steps',[])]
        order_errors=[]
        for i,card in enumerate(used):
            for required in cards.get(card,{}).get('requires',[]):
                if required not in used[:i]:order_errors.append(f'{card} requires {required} earlier')
        # Exact citation format and extracted IDs are distinct checks.
        allowed=set(re.findall(r'CHEMBL\d+|Q\w{5}|proto:[a-z_]+',raw.decode()))
        citations=out.get('citations',[])
        exact_invalid=[c for c in citations if c not in allowed]
        unknown_extracted=sorted({v for c in citations for v in re.findall(r'CHEMBL\d+|Q\w{5}|proto:[a-z_]+',c) if v not in allowed})
        results.append({'case_id':cid,'json_valid':True,'all_contract_fields_present':set(inp['output_contract'])<=out.keys(),'input_sha256_verified':True,'excluded_source_ids_absent_from_input':True,'valid_series_parameters':valid,'series_nM':series,'reference_ic50_nM':truth,'minimum_nM':min(series) if series else None,'maximum_nM':max(series) if series else None,'below_reference':sum(v<truth for v in series),'above_reference':sum(v>truth for v in series),'brackets_reference':bool(series) and min(series)<=truth<=max(series),'at_least_two_each_side':sum(v<truth for v in series)>=2 and sum(v>truth for v in series)>=2,'log10_span':math.log10(max(series)/min(series)) if series else None,'comparability':'Not established; coverage is descriptive only.','unknown_step_cards':[c for c in used if c not in cards],'prerequisite_order_errors':order_errors,'citations_not_exact_ids':exact_invalid,'unknown_extracted_citation_ids':unknown_extracted})
    (RUN/'diagnostics.json').write_text(json.dumps(results,indent=2)+'\n')
    for r in results:print(r['case_id'], 'range nM',r['minimum_nM'],r['maximum_nM'],'below/above',r['below_reference'],r['above_reference'],'exact citation failures',len(r['citations_not_exact_ids']))


if __name__=='__main__':main()
