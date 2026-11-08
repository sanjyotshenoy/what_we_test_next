"""Export repository evidence for the deck; no LLM calls or invented benchmark scores.
Run from the repo root: python -m slides.tools.prep_deck_evidence --execution-dir /tmp/wwtn-mic-evidence
The execution directory must be produced by execution.generate --simulate beforehand.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import yaml
from execution.lab import Lab
from execution.plate import plate_design, audit
from wwtn.schema import ExperimentProposal, ExecutionResult, read_jsonl

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--execution-dir',type=Path,required=True); args=ap.parse_args()
    dest=Path('slides/talks/biohack/evidence');dest.mkdir(exist_ok=True)
    graph=Path('kg/biology/graph_bacteria')
    nodes=list(csv.DictReader((graph/'nodes.csv').open()));edges=list(csv.DictReader((graph/'edges.csv').open()))
    props=[json.loads(e['props']) for e in edges]
    seen=set(); examples=[]; lookup={n['id']:n for n in nodes}
    for edge, measurement in zip(edges,props):
        if edge['dst'] in seen: continue
        seen.add(edge['dst'])
        examples.append({'compound':edge['src'],'organism':lookup[edge['dst']]['name'],
                         'measurement':measurement,'source':edge['source']})
    (dest/'mic_examples.json').write_text(json.dumps({'description':'One committed measurement per organism, for provenance inspection; not a selectivity comparison.', 'records':examples},indent=2)+'\n')
    rules=yaml.safe_load(Path('kg/protocols/rules.yaml').read_text())
    proposal=read_jsonl('execution/examples/mic_selectivity.jsonl',ExperimentProposal)[0]
    design=plate_design(proposal.experiment,Lab.load())
    result=read_jsonl(args.execution_dir/'results.jsonl',ExecutionResult)[0]
    assert result.simulated_ok, 'Do not present an unverified simulation as passing'
    for field,name in [('protocol_path','protocol.py'),('run_sheet_path','run_sheet.md')]:
        shutil.copyfile(getattr(result,field),dest/name)
    shutil.copyfile('execution/examples/mic_selectivity.jsonl',dest/'input.jsonl')
    exported=result.model_dump();exported.update(protocol_path='protocol.py',run_sheet_path='run_sheet.md')
    (dest/'result.json').write_text(json.dumps(exported,indent=2)+'\n')
    data={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
          'graph':{'nodes':len(nodes),'edges':len(edges),'types':dict(Counter(n['type'] for n in nodes)),
                   'censored':sum(p.get('relation')=='>' for p in props),
                   'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [graph/'nodes.csv',graph/'edges.csv']}},
          'rules':{'total':len(rules),'checkable':sum(r.get('check') is not None for r in rules)},
          'plate':asdict(design),'audit_errors':audit(design),'simulation':exported}
    assert not data['audit_errors']
    (dest/'data.json').write_text(json.dumps(data,indent=2)+'\n')
    (dest/'data.js').write_text('window.DATA = window.DATA || {};\nwindow.DATA.evidence = '+json.dumps(data)+';\n')
    print('Exported graph counts, plate map, audit, protocol, run sheet and simulation result.')
if __name__=='__main__':main()
