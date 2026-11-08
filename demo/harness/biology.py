"""MIC-aware, bounded read adapter for the team's bacterial CSV graph.

No kinase helper, unit conversion, imputation, species-level aggregation or
benchmark claims. Raw measurements retain censoring and source identities.
"""
import csv
import hashlib
import json
from demo.harness.paths import ROOT

GRAPH = ROOT / 'kg/biology/graph_bacteria'


def graph_hashes():
    return {name: hashlib.sha256((GRAPH/name).read_bytes()).hexdigest() for name in ('nodes.csv','edges.csv')}


def lookup(compound, species, limit=10):
    if not all(isinstance(x, str) and 1 <= len(x.strip()) <= 150 for x in (compound, species)):
        raise ValueError('Provide compound and species exact names or graph IDs (1–150 characters)')
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('limit must be 1–20')
    with (GRAPH/'nodes.csv').open() as stream:
        nodes = {r['id']: {**r, 'props': json.loads(r['props'])} for r in csv.DictReader(stream)}
    def resolve(text, kind):
        return [n for n in nodes.values() if n['type'] == kind and
                text.strip().casefold() in (n['id'].casefold(), n['name'].casefold())]
    compounds, organisms = resolve(compound, 'Compound'), resolve(species, 'Organism')
    matches, count = [], 0
    resolved = len(compounds) == len(organisms) == 1
    if resolved:
        with (GRAPH/'edges.csv').open() as stream:
            for r in csv.DictReader(stream):
                if r['rel']=='INHIBITS' and r['src']==compounds[0]['id'] and r['dst']==organisms[0]['id']:
                    count += 1
                    if len(matches) < limit:
                        props = json.loads(r['props'])
                        matches.append({**r, 'props': props, 'assay': nodes.get(props.get('assay')),
                                        'document': nodes.get(props.get('document'))})
    result = {'compound_matches': compounds[:5], 'species_matches': organisms[:5],
              'resolution': 'resolved' if resolved else 'unresolved_or_ambiguous',
              'measurements': matches, 'total_measurements': count, 'truncated': count > limit,
              'source_hashes': graph_hashes(),
              'limits': ['Unrestricted demo graph; no benchmark hold-out applied.',
                         'A missing pair means absent from this graph, not scientifically unmeasured.',
                         'Species-level records may hide strain resistance; do not infer selectivity or applicability.',
                         'Traits are hand-curated, not independently sourced. Preserve > censoring and original units.',
                         'Returned measurements are the first rows in graph order, not a representative summary.']}
    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return {**result, 'evidence_id': 'biology:' + digest, 'sha256': digest}
