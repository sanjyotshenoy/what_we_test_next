"""Read-only overview of the bacterial graph; measurement edges are grouped by pair."""
import csv
from collections import Counter
from functools import lru_cache
import json
from demo.harness.biology import GRAPH


def overview():
    signature = tuple((GRAPH / name).stat().st_mtime_ns for name in ('nodes.csv', 'edges.csv'))
    return _overview(str(GRAPH), signature)


@lru_cache(maxsize=2)
def _overview(directory, signature):
    from pathlib import Path
    root = Path(directory)
    with (root / 'nodes.csv').open() as stream:
        records = [{**r, 'props': json.loads(r['props'])} for r in csv.DictReader(stream)]
    nodes = [r for r in records if r['type'] in ('Compound', 'Organism')]
    known = {r['id'] for r in nodes}
    groups = {}
    total = 0
    with (root / 'edges.csv').open() as stream:
        for r in csv.DictReader(stream):
            total += 1
            if r['src'] not in known or r['dst'] not in known:
                continue
            key = (r['src'], r['dst'], r['rel'])
            g = groups.setdefault(key, {'src': r['src'], 'dst': r['dst'], 'rel': r['rel'],
                                       'measurements': 0, 'units': Counter(), 'relations': Counter(),
                                       'assays': set(), 'documents': set()})
            p = json.loads(r['props'])
            g['measurements'] += 1
            g['units'][p.get('unit', 'unspecified')] += 1
            g['relations'][p.get('relation', 'unspecified')] += 1
            if p.get('assay'): g['assays'].add(p['assay'])
            if p.get('document'): g['documents'].add(p['document'])
    for g in groups.values():
        g['assays'] = len(g['assays'])
        g['documents'] = len(g['documents'])
    return {'nodes': nodes, 'edges': list(groups.values()),
            'counts': {'records': len(records), 'types': dict(Counter(r['type'] for r in records)),
                       'measurements': total, 'pairs': len(groups)},
            'note': 'Entire bacterial compound–organism network. Measurements are grouped by pair; '
                    'assay and document records are summarized on edges, not drawn as separate nodes. '
                    'This is current KG context, not additional evidence retrieved by the saved agent.'}
