import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from demo.harness import biology, planning_pipeline as pipeline


class BiologyTests(unittest.TestCase):
    def test_real_graph_censoring_and_units_preserved(self):
        result = biology.lookup('CHEMBL324525', 'CHEMBL614411', 20)
        self.assertEqual(result['resolution'], 'resolved')
        self.assertTrue(any(r['props']['relation']=='>' for r in result['measurements']))
        self.assertTrue(all(r['props']['unit'] in ('ug.mL-1', 'nM') for r in result['measurements']))
        self.assertTrue(all(r['assay'] and r['document'] for r in result['measurements']))
        with TemporaryDirectory() as d, patch.object(pipeline,'RUNS',Path(d)):
            directory = Path(d)/'test'; directory.mkdir()
            record = {'mode':'demo','tool':'biology_lookup','result':result}
            pipeline.save(directory/'kg.json', record)
            self.assertIn(result['evidence_id'],pipeline.evidence_for('test'))
            record['result']['measurements'][0]['props']['mic']=0
            pipeline.save(directory/'kg.json', record)
            self.assertNotIn(result['evidence_id'],pipeline.evidence_for('test'))

    def test_unresolved_fixture_is_not_an_absence_claim(self):
        result = biology.lookup('synthetic fixture', 'synthetic species')
        self.assertEqual(result['resolution'],'unresolved_or_ambiguous')
        self.assertEqual(result['measurements'],[])
        with self.assertRaises(ValueError): biology.lookup('a','b',100)
