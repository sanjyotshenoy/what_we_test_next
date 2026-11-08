"""Three isolated requests via wwtn.llm.chat, with response usage and no retries.
Run from repo root: python -m benchmark.run_three_case_pilot
The source .env is loaded explicitly by the operator before running this module.
"""
import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from wwtn import llm

MODEL = 'openai/gpt-oss-120b'
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'slides/talks/biohack/graph/cases'
DEST = ROOT / 'benchmark/runs/gpt-oss-120b-pilot'
SYSTEM = '''You are participating in an experiment-design pilot. Use only the supplied input packet as evidence. Do not access tools, web, raw graphs, or remembered compound-specific measurements. Select and order step cards, bind supported parameters, and state unresolved settings explicitly. Follow the output_contract. If its numeric fields cannot be justified, use null and explain in limitations rather than inventing evidence. Any provisional design choice must be explicitly labeled as an assumption, not a sourced fact. Distinguish biochemical inhibition, cellular viability, and target-specific causality. Return one valid JSON object only; keep it concise (under 1800 words). Cite only IDs present in the packet. Do not predict a withheld IC50.'''
SETTINGS = {'temperature': 0, 'max_tokens': 8192, 'reasoning_effort': 'low', 'response_format': {'type': 'json_object'}}
RATES = {'input_per_million_usd': .15, 'output_per_million_usd': .60, 'source': 'https://tokenfactory.nebius.com/api/public/models_info', 'checked_utc': '2026-11-08', 'cached_discount_applied': False}


def main():
    logging.disable(logging.CRITICAL)
    DEST.mkdir(parents=True, exist_ok=True)
    if (DEST / 'manifest.json').exists():
        raise SystemExit('Refusing to repeat a paid run; existing manifest found.')
    packets = [(SOURCE / f'case-{i}.input.json').read_bytes() for i in range(1,4)]
    reserve = sum((len(p)+len(SYSTEM.encode())+4096)*.15/1e6 + SETTINGS['max_tokens']*.6/1e6 for p in packets)
    assert reserve < .10
    manifest = {'model': MODEL, 'system_prompt': SYSTEM, 'settings': SETTINGS, 'rates': RATES, 'estimated_conservative_reservation_usd': reserve, 'reservation_method': 'UTF-8 bytes as conservative input-token allowance plus 4096 framing tokens per request; full output cap at uncached list prices', 'max_requests': 3, 'sdk_retries': 0, 'started_utc': datetime.now(timezone.utc).isoformat(), 'requests': []}
    def save():
        (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    bounded = llm.client().with_options(max_retries=0, timeout=180)
    llm.client = lambda: bounded
    receipts = []
    def capture(response):
        response.read()
        if response.status_code == 200:
            body=response.json()
            receipts.append({'response_id': body.get('id'), 'model_returned': body.get('model'), 'usage': body.get('usage'), 'finish_reason': (body.get('choices') or [{}])[0].get('finish_reason')})
    bounded._client.event_hooks.setdefault('response',[]).append(capture)
    for i,packet in enumerate(packets,1):
        cid=f'case-{i}'
        (DEST/f'{cid}.input.json').write_bytes(packet)
        record={'case_id':cid,'input_sha256':hashlib.sha256(packet).hexdigest(),'started_utc':datetime.now(timezone.utc).isoformat(),'status':'started'}
        manifest['requests'].append(record); save()
        before=len(receipts)
        try:
            output=llm.chat(packet.decode(), model=MODEL, system=SYSTEM, **SETTINGS)
            record['status']='completed'
            (DEST/f'{cid}.output.txt').write_text(output or '')
            try:
                parsed=json.loads(output or '')
                (DEST/f'{cid}.output.json').write_text(json.dumps(parsed,indent=2)+'\n')
                record['valid_json']=True
            except (ValueError,TypeError):
                record['valid_json']=False
            if len(receipts) != before+1 or not receipts[-1].get('usage'):
                raise RuntimeError('Missing usage receipt; stop further paid calls')
            record.update(receipts[-1])
            u=record['usage']
            record['estimated_cost_usd']=(u['prompt_tokens']*.15+u['completion_tokens']*.6)/1e6
            print(cid, json.dumps({'usage':u,'estimated_cost_usd':record['estimated_cost_usd'],'finish_reason':record['finish_reason']}),flush=True)
        except Exception as e:
            record['status']='failed_or_usage_unavailable';record['error_type']=type(e).__name__
            record['http_status']=getattr(e,'status_code',None)
            save();raise SystemExit('Run stopped; see sanitized manifest. No automatic retry.')
        finally:
            record['finished_utc']=datetime.now(timezone.utc).isoformat();save()
    manifest['total_prompt_tokens']=sum(r['usage']['prompt_tokens'] for r in manifest['requests'])
    manifest['total_completion_tokens']=sum(r['usage']['completion_tokens'] for r in manifest['requests'])
    manifest['estimated_total_usd']=sum(r['estimated_cost_usd'] for r in manifest['requests'])
    save()


if __name__=='__main__':
    main()
