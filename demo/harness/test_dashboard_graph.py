"""Graph overview retains every measurement while grouping provenance records."""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from demo.harness import dashboard_graph


class OverviewTests(TestCase):
    def test_grouping_preserves_measurement_counts_units_and_censoring(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (root/'nodes.csv').open('w') as f:
                writer = csv.DictWriter(f, fieldnames=['id','type','name','props','source'])
                writer.writeheader()
                for identity, kind in [('c','Compound'),('o','Organism'),('a','Assay'),('d','Document')]:
                    writer.writerow(dict(id=identity,type=kind,name=identity,props='{}',source='test'))
            with (root/'edges.csv').open('w') as f:
                writer = csv.DictWriter(f, fieldnames=['src','dst','rel','props','source'])
                writer.writeheader()
                for unit, relation in [('ug/mL','>'),('nM','=')]:
                    writer.writerow(dict(src='c',dst='o',rel='INHIBITS',source='test',
                        props=json.dumps(dict(unit=unit,relation=relation,assay='a',document='d'))))
            with patch.object(dashboard_graph, 'GRAPH', root):
                result = dashboard_graph.overview()
            self.assertEqual(len(result['nodes']), 2)
            self.assertEqual(result['counts']['records'], 4)
            self.assertEqual(result['counts']['measurements'], 2)
            self.assertEqual(result['edges'][0]['measurements'], 2)
            self.assertEqual(result['edges'][0]['units'], {'ug/mL':1,'nM':1})
            self.assertEqual(result['edges'][0]['relations'], {'>':1,'=':1})
            self.assertEqual(result['edges'][0]['assays'], 1)
