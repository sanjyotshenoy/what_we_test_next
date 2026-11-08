"""Five models, 20 isolated cases; reuse identical original 15 outputs, 85 planned new calls plus one timeout retry and one interrupted-process recovery.
Run with --execute after offline tests. --resume only runs never-started requests.
Credentials are loaded from the operator's local environment, never from stored packets.
"""
import argparse
import hashlib
import json
import logging
import shutil
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from wwtn import llm
from benchmark.run_three_case_pilot import SYSTEM, SETTINGS
from benchmark.run_four_model_pilot import MODELS as FOUR, URL

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'slides/talks/biohack/graph/cases'
DEST = ROOT / 'benchmark/runs/twenty-case-pilot'
MODELS = {**FOUR, 'gpt-oss-120b': 'openai/gpt-oss-120b'}
CAP = 5.0

def now(): return datetime.now(timezone.utc).isoformat()

def preflight():
    available = {m.id for m in llm.client().with_options(timeout=20, max_retries=0).models.list()}
    if not set(MODELS.values()) <= available:
        raise ValueError('Historical model unavailable; no substitutions allowed')
    with urllib.request.urlopen(URL, timeout=20) as response:
        catalog = json.load(response)
    rates = {}
    def walk(x):
        if isinstance(x, dict):
            if x.get('model_id') in MODELS.values() and 'input_price_per_million_tokens' in x:
                rates[x['model_id']] = {k: x[k] for k in ('input_price_per_million_tokens', 'output_price_per_million_tokens')}
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(catalog)
    assert len(rates) == 5
    packets = {f'case-{i}': (SOURCE / f'case-{i}.input.json').read_bytes() for i in range(1, 21)}
    reserve = sum((len(p) + len(SYSTEM.encode()) + 4096) * rates[mid]['input_price_per_million_tokens'] / 1e6 + SETTINGS['max_tokens'] * rates[mid]['output_price_per_million_tokens'] / 1e6 for mid in MODELS.values() for cid, p in packets.items() if int(cid.split('-')[1]) > 3)
    if not 0 < reserve <= CAP: raise ValueError('Reservation exceeds local $5 ceiling')
    return rates, packets, reserve

def main():
    ap = argparse.ArgumentParser();ap.add_argument('--execute', action='store_true');ap.add_argument('--resume', action='store_true');ap.add_argument('--retry-timeout', action='store_true');ap.add_argument('--recover-interrupted', action='store_true');args = ap.parse_args()
    logging.disable(logging.CRITICAL)
    try: rates, packets, reserve = preflight()
    except Exception as e: raise SystemExit('Preflight stopped: ' + type(e).__name__)
    print(json.dumps({'models': MODELS, 'rates': rates, 'base_planned_new_requests': 85, 'base_reservation_usd': reserve, 'ceiling_usd': CAP}), flush=True)
    if not args.execute: return
    DEST.mkdir(parents=True, exist_ok=True);path = DEST / 'manifest.json';lock = threading.Lock();halt = threading.Event()
    if path.exists():
        if not args.resume: raise SystemExit('Existing run; refusing duplicate generation')
        manifest = json.loads(path.read_text())
        manifest.pop('finished_utc', None)
        assert manifest['rates'] == rates and manifest['settings'] == SETTINGS and manifest['system_prompt'] == SYSTEM
        if args.recover_interrupted:
            interrupted = [r for r in manifest['requests'] if r['status'] == 'started']
            assert len(interrupted) == 1 and not manifest.get('explicit_interruption_retries')
            lost = interrupted[0];rate = rates[lost['model']];packet = packets[lost['case_id']]
            lost['status'] = 'interrupted_without_receipt';lost['finished_utc'] = now()
            lost['unconfirmed_cost_reservation_usd'] = ((len(packet) + len(SYSTEM.encode()) + 4096) * rate['input_price_per_million_tokens'] + SETTINGS['max_tokens'] * rate['output_price_per_million_tokens']) / 1e6
            manifest.setdefault('failed_attempts', []).append(lost);manifest['requests'].remove(lost)
            manifest['unconfirmed_cost_reservation_usd'] = sum(r['unconfirmed_cost_reservation_usd'] for r in manifest['failed_attempts'])
            manifest['estimated_conservative_reservation_usd'] = reserve + manifest['unconfirmed_cost_reservation_usd']
            manifest['max_new_requests'] = 85 + len(manifest['failed_attempts'])
            manifest['explicit_interruption_retries'] = 1
            assert manifest['estimated_conservative_reservation_usd'] < CAP
        if args.retry_timeout:
            failed = [r for r in manifest['requests'] if r['status'] == 'failed_or_usage_unavailable']
            assert len(failed) == 1 and failed[0].get('error_type') == 'APITimeoutError'
            assert failed[0]['case_id'] not in {r['case_id'] for r in manifest.get('failed_attempts', [])}, 'Only one explicit retry per case allowed'
            lost = failed[0];rate = rates[lost['model']];packet = packets[lost['case_id']]
            lost['unconfirmed_cost_reservation_usd'] = ((len(packet) + len(SYSTEM.encode()) + 4096) * rate['input_price_per_million_tokens'] + SETTINGS['max_tokens'] * rate['output_price_per_million_tokens']) / 1e6
            manifest.setdefault('failed_attempts', []).append(lost)
            manifest['requests'].remove(lost)
            manifest['unconfirmed_cost_reservation_usd'] = sum(r['unconfirmed_cost_reservation_usd'] for r in manifest['failed_attempts'])
            manifest['estimated_conservative_reservation_usd'] = reserve + manifest['unconfirmed_cost_reservation_usd']
            manifest['max_new_requests'] = 85 + len(manifest['failed_attempts'])
            manifest['explicit_timeout_retries'] = manifest.get('explicit_timeout_retries', 0) + 1
            assert manifest['estimated_conservative_reservation_usd'] < CAP
        assert not any(r['status'] not in ('completed', 'reused') for r in manifest['requests']), 'Ambiguous/failed receipt: manual reconciliation required'
    else:
        manifest = {'started_utc': now(), 'model_mapping': MODELS, 'system_prompt': SYSTEM, 'settings': SETTINGS, 'rates': rates, 'pricing_source': URL, 'estimated_conservative_reservation_usd': reserve, 'budget_ceiling_usd': CAP, 'max_new_requests': 85, 'sdk_retries': 0, 'max_concurrency': 5, 'reuse_policy': 'Original cases 1–3 reused only with identical packet bytes, system prompt and settings; historical receipts and source paths retained.', 'requests': []}
        for slug, mid in MODELS.items():
            old = ROOT / ('benchmark/runs/gpt-oss-120b-pilot' if slug == 'gpt-oss-120b' else 'benchmark/runs/four-model-pilot')
            om = json.loads((old / 'manifest.json').read_text());assert om['system_prompt'] == SYSTEM and om['settings'] == SETTINGS
            folder = old if slug == 'gpt-oss-120b' else old / slug
            dest = DEST / slug;dest.mkdir(exist_ok=True)
            for i in range(1, 4):
                cid = f'case-{i}';assert (folder / f'{cid}.input.json').read_bytes() == packets[cid]
                rec = next(r for r in om['requests'] if r['case_id'] == cid and (slug == 'gpt-oss-120b' or r['slug'] == slug))
                assert rec['status'] == 'completed'
                for suffix in ('input.json', 'output.json', 'output.txt'): shutil.copyfile(folder / f'{cid}.{suffix}', dest / f'{cid}.{suffix}')
                manifest['requests'].append({**rec, 'slug': slug, 'model': mid, 'status': 'reused', 'reused_from': str(folder.relative_to(ROOT)), 'new_cost_usd': 0})
    def save():
        rows = manifest['requests'];new = [r for r in rows if r['status'] != 'reused']
        manifest['new_prompt_tokens'] = sum(r.get('usage', {}).get('prompt_tokens', 0) for r in new)
        manifest['new_completion_tokens'] = sum(r.get('usage', {}).get('completion_tokens', 0) for r in new)
        manifest['estimated_new_cost_usd'] = sum(r.get('estimated_cost_usd', 0) for r in new)
        tmp = path.with_suffix('.tmp');tmp.write_text(json.dumps(manifest, indent=2) + '\n');tmp.replace(path)
    save()
    base = llm.client();local = threading.local();llm.client = lambda: local.client
    def run_model(slug, mid):
        local.client = base.with_options(max_retries=0, timeout=600 if args.retry_timeout else (300 if args.recover_interrupted else 180))
        # Each worker needs its own HTTP hooks; capture usage by wrapping only its completion method.
        create = local.client.chat.completions.create
        receipt = {}
        def capture(**kwargs):
            response = create(**kwargs)
            receipt.clear();receipt.update({'response_id': response.id, 'model_returned': response.model, 'usage': response.usage.model_dump() if response.usage else None, 'finish_reason': response.choices[0].finish_reason})
            return response
        local.client.chat.completions.create = capture
        folder = DEST / slug;folder.mkdir(exist_ok=True)
        for cid, packet in packets.items():
            with lock:
                if halt.is_set(): return
                if any(r['slug'] == slug and r['case_id'] == cid for r in manifest['requests']): continue
                rec = {'slug': slug, 'model': mid, 'case_id': cid, 'input_sha256': hashlib.sha256(packet).hexdigest(), 'started_utc': now(), 'status': 'started', 'timeout_seconds': 600 if args.retry_timeout else (300 if args.recover_interrupted else 180)}
                manifest['requests'].append(rec);save()
            (folder / f'{cid}.input.json').write_bytes(packet)
            try:
                output = llm.chat(packet.decode(), model=mid, system=SYSTEM, **SETTINGS)
                (folder / f'{cid}.output.txt').write_text(output or '')
                if not receipt.get('usage'): raise RuntimeError('Missing usage')
                rec.update(receipt);u = rec['usage'];rate = rates[mid]
                rec['estimated_cost_usd'] = (u['prompt_tokens'] * rate['input_price_per_million_tokens'] + u['completion_tokens'] * rate['output_price_per_million_tokens']) / 1e6
                try:
                    parsed = json.loads(output or '');assert isinstance(parsed, dict)
                    (folder / f'{cid}.output.json').write_text(json.dumps(parsed, indent=2, allow_nan=False) + '\n');rec['valid_json'] = True
                except (ValueError, AssertionError): rec['valid_json'] = False
                rec['status'] = 'completed'
                print(slug, cid, 'completed', rec['finish_reason'], flush=True)
            except Exception as e:
                rec['status'] = 'failed_or_usage_unavailable';rec['error_type'] = type(e).__name__;rec['http_status'] = getattr(e, 'status_code', None);halt.set()
                print(slug, cid, 'STOPPED', type(e).__name__, flush=True)
            finally:
                rec['finished_utc'] = now()
                with lock: save()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(run_model, slug, mid) for slug, mid in MODELS.items()]
        for future in futures: future.result()
    manifest['finished_utc'] = now();save()
    print(json.dumps({k: manifest[k] for k in ('new_prompt_tokens', 'new_completion_tokens', 'estimated_new_cost_usd')}), flush=True)

if __name__ == '__main__': main()
