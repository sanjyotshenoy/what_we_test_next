"""Run the same three isolated packets against four explicitly selected models.
python -m benchmark.run_four_model_pilot
No automatic retries, max 12 paid requests, conservative $1 reservation gate.
"""
import hashlib
import json
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from wwtn import llm
from benchmark.run_three_case_pilot import SYSTEM, SETTINGS

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'benchmark/runs/gpt-oss-120b-pilot'
DEST=ROOT/'benchmark/runs/four-model-pilot'
MODELS={'glm-5.3':'zai-org/GLM-5.3','deepseek-v4.1-flash-1017':'deepseek-ai/DeepSeek-V4.1-Flash-1017','kimi-k3.1-pro':'moonshotai/Kimi-K3.1-Pro','nemotron-3-super':'nvidia/nemotron-3-super-120b-a12b'}
URL='https://tokenfactory.nebius.com/api/public/models_info'


def main():
 logging.disable(logging.CRITICAL)
 DEST.mkdir(parents=True,exist_ok=True)
 path=DEST/'manifest.json'
 if path.exists():raise SystemExit('Existing run found; refusing repeat paid calls.')
 packets=[(SOURCE/f'case-{i}.input.json').read_bytes() for i in range(1,4)]
 available={m.id for m in llm.client().with_options(timeout=20,max_retries=0).models.list()}
 assert set(MODELS.values())<=available
 with urllib.request.urlopen(URL,timeout=20) as r:catalog=json.load(r)
 rates={}
 def walk(x):
  if isinstance(x,dict):
   if x.get('model_id') in MODELS.values() and 'input_price_per_million_tokens' in x:rates[x['model_id']]={k:v for k,v in x.items() if k in ['model_id','model_name','input_price_per_million_tokens','input_cached_price_per_million_tokens','output_price_per_million_tokens']}
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(catalog)
 assert len(rates)==4
 reserve=sum(sum((len(p)+len(SYSTEM.encode())+4096)*rates[mid]['input_price_per_million_tokens']/1e6+SETTINGS['max_tokens']*rates[mid]['output_price_per_million_tokens']/1e6 for p in packets) for mid in MODELS.values())
 assert reserve<1.0,reserve
 manifest={'started_utc':datetime.now(timezone.utc).isoformat(),'system_prompt':SYSTEM,'settings':SETTINGS,'model_mapping':MODELS,'deepseek_name_resolution':'User said V5.1 Flash 1017; selected V4.1 Flash 1017 based on available catalog and earlier conversation.','rates':rates,'pricing_source':URL,'estimated_conservative_reservation_usd':reserve,'budget_ceiling_usd':1.0,'reservation_method':'UTF-8 bytes + 4096 framing tokens per request, full output cap, uncached list prices','max_requests':12,'sdk_retries':0,'requests':[]}
 def save():path.write_text(json.dumps(manifest,indent=2)+'\n')
 save(); print('PRECHECK reservation USD:',reserve,flush=True)
 bounded=llm.client().with_options(max_retries=0,timeout=180)
 llm.client=lambda:bounded
 receipts=[]
 def capture(response):
  response.read()
  if response.status_code==200:
   body=response.json();receipts.append({'response_id':body.get('id'),'model_returned':body.get('model'),'usage':body.get('usage'),'finish_reason':(body.get('choices') or [{}])[0].get('finish_reason')})
 bounded._client.event_hooks.setdefault('response',[]).append(capture)
 for slug,mid in MODELS.items():
  folder=DEST/slug;folder.mkdir(exist_ok=True)
  for i,packet in enumerate(packets,1):
   cid=f'case-{i}';(folder/f'{cid}.input.json').write_bytes(packet)
   rec={'model':mid,'slug':slug,'case_id':cid,'input_sha256':hashlib.sha256(packet).hexdigest(),'started_utc':datetime.now(timezone.utc).isoformat(),'status':'started'}
   manifest['requests'].append(rec);save();before=len(receipts)
   try:
    output=llm.chat(packet.decode(),model=mid,system=SYSTEM,**SETTINGS)
    (folder/f'{cid}.output.txt').write_text(output or '')
    rec['status']='completed'
    try:
     parsed=json.loads(output or '');(folder/f'{cid}.output.json').write_text(json.dumps(parsed,indent=2)+'\n');rec['valid_json']=True
    except (ValueError,TypeError):rec['valid_json']=False
    if len(receipts)!=before+1 or not receipts[-1].get('usage'):raise RuntimeError('Missing usage; stop spend')
    rec.update(receipts[-1]);u=rec['usage'];rate=rates[mid]
    rec['estimated_cost_usd']=(u['prompt_tokens']*rate['input_price_per_million_tokens']+u['completion_tokens']*rate['output_price_per_million_tokens'])/1e6
    print(slug,cid,json.dumps({'usage':u,'cost_usd':rec['estimated_cost_usd'],'finish':rec['finish_reason'],'json':rec['valid_json']}),flush=True)
   except Exception as e:
    rec['status']='failed_or_usage_unavailable';rec['error_type']=type(e).__name__;rec['http_status']=getattr(e,'status_code',None)
    # Save only structured error type/code, never request content or headers.
    if isinstance(getattr(e,'body',None),dict):rec['provider_error_code']=e.body.get('code')
    save();raise SystemExit('Stopped on error; no retries. See sanitized manifest.')
   finally:rec['finished_utc']=datetime.now(timezone.utc).isoformat();save()
 manifest['total_prompt_tokens']=sum(r['usage']['prompt_tokens'] for r in manifest['requests'])
 manifest['total_completion_tokens']=sum(r['usage']['completion_tokens'] for r in manifest['requests'])
 manifest['estimated_total_usd']=sum(r['estimated_cost_usd'] for r in manifest['requests']);save()


if __name__=='__main__':main()
