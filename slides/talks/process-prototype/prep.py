"""Export selected literal MIC source rows; no inference or shared graph modification.
Run python3 -m slides.talks.process-prototype.prep from repo root.
"""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
nodes={n['id']:n for n in csv.DictReader((ROOT/'kg/biology/graph_bacteria/nodes.csv').open())}
edges=[e for e in csv.DictReader((ROOT/'kg/biology/graph_bacteria/edges.csv').open()) if e['src']=='CHEMBL420452']
panel=['CHEMBL614965','CHEMBL362','CHEMBL614411','CHEMBL613911']
records=[]
for i in panel:
 rows=[]
 for e in edges:
  if e['dst']==i:
   p=json.loads(e['props']);rows.append({'measurement':p,'assay':nodes[p['assay']],'document':nodes[p['document']]})
 records.append({'id':i,'name':nodes[i]['name'],'rows':rows})
template=json.loads((ROOT/'kg/protocols/templates/bacterial_mic_broth.json').read_text())
data={'compound':'CHEMBL420452','panel':records,'dilution_evidence':template['parameters']['dilution_factor']['observed'][0]}
Path(__file__).with_name('data.js').write_text('window.DATA=window.DATA||{};window.DATA.process='+json.dumps(data)+';\n')
