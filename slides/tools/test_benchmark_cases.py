"""Offline invariants for the 20-case packet suite; no API calls.
Run: python3 -m unittest slides.tools.test_benchmark_cases
"""
import hashlib
import json
import math
import unittest
from .prep_benchmark_cases import OUT, ROOT, SPECS, read_graph


class CaseSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nodes, cls.edges = read_graph('biology')
        cls.nodes = {n['id']: n for n in nodes}
        cls.manifest = json.loads((OUT / 'manifest.json').read_text())
        cls.cases = [json.loads((OUT / f'case-{i}.review.json').read_text()) for i in range(1, 21)]

    def test_twenty_distinct_queries_and_document_groups(self):
        self.assertEqual(len(SPECS), 20)
        self.assertEqual(self.manifest['counts_by_mode'], {'biochemical': 15, 'cellular': 5})
        seen_compounds, seen_smiles, seen_documents = set(), set(), set()
        for c in self.cases:
            compound = c['input']['entities'][0]['id']
            smiles = self.nodes[compound]['props'].get('smiles')
            self.assertNotIn(compound, seen_compounds)
            if smiles:
                self.assertNotIn(smiles, seen_smiles)
                seen_smiles.add(smiles)
            docs = set(c['audit']['excluded_documents'])
            self.assertFalse(docs & seen_documents, c['id'])
            seen_documents.update(docs)
            seen_compounds.add(compound)

    def test_truth_and_exclusion_closure_against_raw_graph(self):
        for c in self.cases:
            with self.subTest(case=c['id']):
                comp, target = (e['id'] for e in c['input']['entities'])
                pair = [e for e in self.edges if e['rel'] == 'INHIBITS' and e['src'] == comp and e['dst'] == target]
                truth = c['answer']['reference_measurement']
                self.assertTrue(any(e['props'] == truth for e in pair))
                self.assertTrue(math.isfinite(truth['ic50_nM']) and truth['ic50_nM'] > 0)
                docs = {e['props']['document'] for e in pair}
                assays = {e['src'] for e in self.edges if e['rel'] == 'FROM_DOC' and e['dst'] in docs}
                assays.update(e['props']['assay'] for e in self.edges if e['props'].get('document') in docs and 'assay' in e['props'])
                self.assertEqual(docs, set(c['audit']['excluded_documents']))
                self.assertEqual(assays, set(c['audit']['excluded_assays']))
                blocked = docs | assays
                removed = [e for e in self.edges if e['src'] in blocked or e['dst'] in blocked or e['props'].get('document') in docs or e['props'].get('assay') in assays or e in pair]
                self.assertEqual(len(removed), c['audit']['removed_edges'])
                raw = (OUT / f"{c['id']}.input.json").read_text()
                self.assertFalse(any(x in raw for x in blocked), c['id'])
                self.assertNotIn('reference_measurement', raw)
                self.assertEqual(json.loads(raw), c['input'])
                for example in c['input']['retained_measurement_examples']:
                    self.assertNotEqual(example['compound'], comp)
                    self.assertNotIn(example['document'], docs)
                    self.assertNotIn(example['assay'], assays)
                    self.assertTrue(any(e['src'] == example['compound'] and e['dst'] == target and e['props'].get('assay') == example['assay'] and e['props'].get('ic50_nM') == example['ic50_nM'] for e in self.edges))

    def test_original_pilot_packets_unchanged(self):
        root = ROOT
        for i in range(1, 4):
            old = root / f'benchmark/runs/gpt-oss-120b-pilot/case-{i}.input.json'
            self.assertEqual(json.loads(old.read_text()), json.loads((OUT / f'case-{i}.input.json').read_text()))

    def test_manifest_hashes_and_step_prerequisites(self):
        for entry, c in zip(self.manifest['cases'], self.cases):
            self.assertEqual(entry['id'], c['id'])
            self.assertEqual(entry['input_sha256'], hashlib.sha256((OUT / f"{c['id']}.input.json").read_bytes()).hexdigest())
            seen = set()
            for card in c['input']['step_cards']:
                self.assertTrue(set(card.get('requires', [])) <= seen)
                self.assertNotIn(card['id'], seen)
                seen.add(card['id'])


if __name__ == '__main__':
    unittest.main()
