"""Export committed biology/protocol CSVs for the static graph explorer.

Run from repository root: python -m slides.tools.prep_graph_explorer
Preserves row properties, provenance and parallel edges; never infers missing facts.
"""
import csv
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    nodes = {}
    edges = []
    for graph in ('biology', 'protocols'):
        folder = root / 'kg' / graph / 'graph'
        for kind in ('nodes', 'edges'):
            with (folder / f'{kind}.csv').open(newline='') as handle:
                for row in csv.DictReader(handle):
                    row['props'] = json.loads(row['props'] or '{}')
                    row['graph'] = graph
                    if kind == 'nodes':
                        nodes.setdefault(row['id'], row)
                    else:
                        edges.append(row)
    payload = {'nodes': list(nodes.values()), 'edges': edges}
    dest = root / 'slides/talks/biohack/graph/data.js'
    dest.write_text('window.GRAPH_DATA=' + json.dumps(payload, ensure_ascii=True, separators=(',', ':')) + ';\n')
    print(f'Exported {len(nodes)} nodes and {len(edges)} edges to {dest}')


if __name__ == '__main__':
    main()
