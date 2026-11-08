"""Metadata helper for the host's fresh-agent scheduling. Does not invoke models."""
import argparse,json
from datetime import datetime,timezone
from .validate import OUT,validate

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',nargs=2,metavar=('ITEM','AGENT'));p.add_argument('--next',type=int,default=0);a=p.parse_args()
    path=OUT/'execution.json';log=json.loads(path.read_text())
    events=log['events']
    latest={e['packet_id']:e for e in events if e.get('phase')=='production'}
    for key,e in list(latest.items()):
        g=OUT/'grades'/f'{key}.json'
        if e['status']=='started' and g.exists():
            packet=json.loads((OUT/'packets'/f'{key}.json').read_text())
            errors=validate(packet,json.loads(g.read_text()))
            if errors:print('INVALID',key,errors);continue
            event={**e,'status':'completed','timestamp_utc':datetime.now(timezone.utc).isoformat()};events.append(event);latest[key]=event
    if a.start:
        key,agent=a.start
        assert key not in latest
        events.append({'packet_id':key,'phase':'production','agent_id':agent,'model':'gpt-6-astra','reasoning_effort':'medium','fork_turns':'none','status':'started','timestamp_utc':datetime.now(timezone.utc).isoformat()});latest[key]=events[-1]
    path.write_text(json.dumps(log,indent=2)+'\n')
    jobs=json.loads((OUT/'manifest.json').read_text())['jobs']
    if a.next:print('\n'.join(j['item_id'] for j in jobs if j['item_id'] not in latest) .splitlines()[:a.next])
    print('completed',sum(e['status']=='completed' for e in latest.values()),'active',[k for k,e in latest.items() if e['status']=='started'])
if __name__=='__main__':main()
