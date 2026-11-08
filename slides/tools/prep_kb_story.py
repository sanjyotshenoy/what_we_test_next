"""Export literal kinase/protocol CSV topology for slides, with case-1 exclusions.
Run python3 -m slides.tools.prep_kb_story. Coordinates are illustrative, not similarity.
No shared graph mutation or model calls. Case packet remains the evaluation boundary.
"""
import csv, json, hashlib, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'slides/talks/biohack/data'
def main():
    nodes={}; edges=[]; hashes={}
    for part in ('biology','protocols'):
        for kind in ('nodes','edges'):
            p=ROOT/f'kg/{part}/graph/{kind}.csv'
            hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
            for r in csv.DictReader(p.open()):
                r['props']=json.loads(r['props']); r['kb']=part
                if kind=='nodes': nodes[r['id']]=r
                else: edges.append(r)
    review=json.loads((ROOT/'slides/talks/biohack/graph/cases/case-1.review.json').read_text())
    audit=review['audit']; hidden=set(audit['excluded_documents']+audit['excluded_assays'])
    def blocked(e):
        return e['kb']=='biology' and (e['src'] in hidden or e['dst'] in hidden or e['props'].get('document') in audit['excluded_documents'] or e['props'].get('assay') in audit['excluded_assays'] or (e['src']=='CHEMBL4278808' and e['dst']=='Q8TF76' and e['rel']=='INHIBITS'))
    removed=[e for e in edges if blocked(e)]
    assert len(removed)==audit['removed_edges']
    assert all(hashes[k]==v for k,v in audit['source_sha256'].items()), 'Case snapshot changed; regenerate/audit cases first'
    focus={e[k] for e in removed for k in ('src','dst')}
    focus.update(('Q8TF76','CHEMBL4278808'))
    focus.update(x['compound'] for x in review['input']['retained_measurement_examples'])
    focus.update(('chembl_class:293','chembl_class:158','chembl_class:1100','proto:kinase_biochem_lum'))
    # Keep every excluded edge endpoint in view. Columns expose actual relation types.
    groups={t:sorted(i for i in focus if nodes[i]['type']==t) for t in ('Compound','Target','Assay','Document')}
    pos={}
    for t,x in [('Compound',-230),('Target',-50),('Assay',100),('Document',250)]:
        ids=groups[t]
        for j,i in enumerate(ids): pos[i]=(x,(j-(len(ids)-1)/2)*min(46,320/max(1,len(ids)-1)))
    for j,i in enumerate(('chembl_class:293','chembl_class:158','chembl_class:1100','proto:kinase_biochem_lum')):
        pos[i]=(-50+j*100,220)
    ordered=sorted(nodes); idx={i:j for j,i in enumerate(ordered)}
    ns=[]
    for j,i in enumerate(ordered):
        n=nodes[i]
        if i in pos: x,y=pos[i]
        else:
            h=int(hashlib.sha256(i.encode()).hexdigest()[:12],16); a=(h%100000)/100000*math.tau; radius=600+(h//100000%600)
            x,y=math.cos(a)*radius,math.sin(a)*radius
        ns.append([i,n['type'],n['name'],round(x,2),round(y,2),n['kb']=='protocols',i in hidden,i in focus])
    es=[]; dangling=0
    for e in edges:
        if e['src'] not in idx or e['dst'] not in idx: dangling+=1; continue
        es.append([idx[e['src']],idx[e['dst']],e['rel'],blocked(e),e['kb']=='protocols'])
    data={'nodes':ns,'edges':es,'edge_count':len(edges),'dangling_edges':dangling,'removed_edges':len(removed),'source_sha256':hashes,'excluded_edges':removed,'excluded_nodes':sorted(hidden)}
    out=json.dumps(data,separators=(',',':'),ensure_ascii=False)
    (OUT/'kb_story.json').write_text(out+'\n'); (OUT/'kb_story.js').write_text('window.DATA=window.DATA||{};window.DATA.kb_story='+out+';\n')
    print(f'{len(ns)} nodes, {len(es)} drawable edges, {dangling} dangling; {len(removed)} exclusions')
if __name__=='__main__': main()
