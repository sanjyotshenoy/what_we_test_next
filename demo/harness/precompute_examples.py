"""Run independent planner sessions; never changes the operator's selected model/session.

Receipts are private. Publication requires explicit review of completed artifacts.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path
from demo.harness.paths import DEMO
from demo.harness.stage.server import oc
from demo.harness.stage.planning_view import snapshot

MODELS = ['zai-org/GLM-5.3', 'moonshotai/Kimi-K3',
          'Qwen/Qwen3.8-27B', 'deepseek-ai/DeepSeek-V4-Pro-0813']
QUERIES = ['ciprofloxacin-panel', 'antibiotic-comparison']

async def run(model, query):
    prompt = (DEMO / 'examples' / (query + '.txt')).read_text()
    session = (await oc('POST', '/session', {'title': f'precompute {query} {model}'}))['id']
    record = {'session': session, 'model': model, 'query': query, 'status': 'started'}
    receipt = DEMO / 'private' / 'precomputed' / (session + '.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(record, indent=2)); receipt.chmod(0o600)
    print(json.dumps(record), flush=True)
    try:
        await oc('POST', f'/session/{session}/prompt_async', {
            'agent': 'planner', 'model': {'providerID': 'nebius', 'modelID': model},
            'parts': [{'type': 'text', 'text': prompt}]})
        start = time.monotonic(); stable = 0
        while time.monotonic() - start < 600:
            await asyncio.sleep(3)
            statuses = await oc('GET', '/session/status')
            messages = await oc('GET', f'/session/{session}/message')
            assistants = [m for m in messages if m.get('info', {}).get('role') == 'assistant']
            done = (assistants and assistants[-1]['info'].get('time', {}).get('completed')
                    and statuses.get(session, {}).get('type', 'idle') == 'idle')
            stable = stable + 1 if done else 0
            if stable >= 2:
                break
        else:
            await oc('POST', f'/session/{session}/abort')
            record['status'] = 'timeout'
        data = snapshot(session)
        runs = [r for b in data['batches'] for r in b['runs']]
        errors = [m['info']['error'].get('name', 'error') for m in assistants if m['info'].get('error')]
        verified = len(runs) == 2 and all(r.get('simulation', {}).get('status') == 'passed' for r in runs if r.get('simulation')) and all(r.get('simulation') for r in runs)
        record.update(status='verified' if verified and not errors else record.get('status') if record.get('status') == 'timeout' else 'incomplete',
                      run_count=len(runs), errors=errors, elapsed_s=round(time.monotonic()-start, 1))
    except Exception as exc:
        record.update(status='error', error_type=type(exc).__name__)
    receipt.write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)

async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--query', choices=QUERIES)
    args=parser.parse_args()
    for model in [args.model] if args.model else MODELS:
        for query in [args.query] if args.query else QUERIES:
            await run(model, query)

if __name__ == '__main__':
    asyncio.run(main())
