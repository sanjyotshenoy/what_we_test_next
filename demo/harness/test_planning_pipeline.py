"""Offline integration fixtures, not biological proposals or real evidence."""
import copy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from demo.harness import planning_pipeline as p


def fixture_batch(compounds=3, species=3):
    """Deliberately named synthetic inputs exercise plumbing, not assay validity."""
    items = []
    for i in range(compounds):
        experiment = {'assay_type': 'broth microdilution MIC', 'readout': 'absorbance OD590',
                      'system': 'synthetic fixture panel',
                      'panel': [{'name': f'fixture species {j}', 'role': 'unknown',
                                 'oxygen_tolerance': 'aerobe', 'reason': 'synthetic software test'} for j in range(species)],
                      'top_concentration': 50, 'concentration_unit': 'uM', 'dilution_factor': 2,
                      'n_points': 10, 'replicates': 2, 'controls': ['growth control', 'sterility control'],
                      'medium': 'cation-adjusted Mueller-Hinton broth', 'incubation_C': 37,
                      'incubation_h': 18, 'atmosphere': 'aerobic', 'well_volume_uL': 200,
                      'layout': {'plate_format': 96, 'series_axis': 'columns', 'replicates_axis': 'rows',
                                 'control_columns': ['growth control', 'sterility control']}}
        items.append({'compound': f'fixture compound {i}',
                      'proposal': {'question_id': f'fixture-{i}', 'answerable_from_kb': False,
                                   'experiment': experiment, 'citations': [p.TEMPLATE_ID],
                                   'rationale': 'Synthetic integration fixture; not biological evidence.',
                                   'model': 'test fixture'},
                      'evidence_links': [{'field': f, 'kind': 'input', 'citations': [],
                                          'explanation': 'Explicit synthetic test input'} for f in sorted(p.FIELDS)]})
    return {'template_id': p.TEMPLATE_ID, 'compounds': items, 'open_questions': []}


def seed_context(session):
    directory = p.session_dir(session)
    directory.mkdir(parents=True, exist_ok=True)
    p.save(directory / 'fixture-context.json', {'mode': 'demo', 'tool': 'planning_context',
        'result': {'evidence_id': p.TEMPLATE_ID, 'source_hashes':
                   {str(f.relative_to(p.ROOT)): p.sha(f) for f in (p.TEMPLATE, p.LAB)}}})


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch = patch.object(p, 'RUNS', Path(self.temp.name))
        self.patch.start(); self.addCleanup(self.patch.stop)
        seed_context('test')

    def test_three_by_three_compiles_distinct_sources_and_complete_maps(self):
        result = p.submit(fixture_batch(), 'test')
        self.assertEqual(result['status'], 'compiled', result)
        self.assertEqual(result['run_count'], 9)
        directory = Path(result['manifest']).parent
        manifest = json.loads(Path(result['manifest']).read_text())
        identities = set()
        for run in manifest['runs']:
            mapping = json.loads((directory / run['sources']).read_text())
            identities.add((mapping['A2']['identity'], mapping['A3']['identity']))
            plate = json.loads((directory / run['plate']).read_text())
            self.assertEqual(len(plate['design']['wells']), 96)
            self.assertIn('final_concentration', plate['design']['wells'][0])
            self.assertNotIn('final_uM', plate['design']['wells'][0])
            self.assertEqual(run['allocation']['requested_rows'], 'AB')
            self.assertEqual(run['allocation']['surplus_rows'], 'CDEFGH')
            self.assertEqual(run['simulation']['status'], 'not_run')
            self.assertEqual(plate['audit_errors'], [])
        self.assertEqual(len(identities), 9)
        self.assertEqual(len((directory / 'proposals.jsonl').read_text().splitlines()), 3)

    def test_unsupported_designs_are_rejected_without_protocols(self):
        mutations = [lambda e: e.update(dilution_factor=3),
                     lambda e: e.update(top_concentration=float('nan')),
                     lambda e: e.update(concentration_unit='percent'),
                     lambda e: e.update(controls=e['controls']+['reference antibiotic']),
                     lambda e: e.update(assay_type='kinase IC50'),
                     lambda e: e['panel'][0].update(oxygen_tolerance='unknown'),
                     lambda e: e.update(atmosphere='anaerobic'),
                     lambda e: e['layout'].update(series_axis='rows'),
                     lambda e: e.update(readout='fluorescence')]
        mutations.append(lambda e: e.update(n_points=3))  # required KG rule: >=8
        mutations.append(lambda e: e['panel'][0].update(name='"""; injected_code() #'))
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                batch = fixture_batch(1, 1)
                mutate(batch['compounds'][0]['proposal']['experiment'])
                self.assertEqual(p.submit(batch, 'test')['status'], 'rejected')
        self.assertFalse(list(Path(self.temp.name).rglob('protocol.py')))

    def test_unread_or_cross_session_citation_rejected(self):
        batch = fixture_batch(1, 1)
        batch['compounds'][0]['proposal']['citations'].append('paper:made-up')
        self.assertEqual(p.submit(batch, 'test')['status'], 'rejected')
        self.assertEqual(p.submit(fixture_batch(1, 1), 'different-session')['status'], 'rejected')
        passage = 'L1: synthetic source fixture'
        digest = p.hashlib.sha256(passage.encode()).hexdigest()
        identifier = f'paper:PMC1:L1-L1:{digest[:12]}'
        record = {'mode': 'demo', 'tool': 'literature_read', 'args': {'paper_id': 'PMC1'},
                  'result': {'evidence_id': identifier, 'passage': passage,
                             'sha256': digest, 'start': 1, 'end': 1}}
        path = p.session_dir('test') / 'paper-fixture.json'
        p.save(path, record)
        self.assertIn(identifier, p.evidence_for('test'))
        record['result']['passage'] = 'L1: tampered'
        p.save(path, record)
        self.assertNotIn(identifier, p.evidence_for('test'))

    def test_missing_field_and_open_question_rejected(self):
        batch = fixture_batch(1, 1)
        batch['compounds'][0]['evidence_links'].pop()
        self.assertEqual(p.submit(batch, 'test')['status'], 'rejected')

    def test_optional_background_links_are_not_rejected(self):
        batch = fixture_batch(1, 1)
        batch['compounds'][0]['evidence_links'].append({'field': 'background', 'kind': 'default',
            'citations': [p.TEMPLATE_ID], 'explanation': 'Template context'})
        self.assertEqual(p.submit(batch, 'test')['status'], 'compiled')
        batch = fixture_batch(1, 1); batch['open_questions'] = ['missing compound solubility']
        self.assertEqual(p.submit(batch, 'test')['status'], 'rejected')

    def test_plate_audit_is_a_hard_gate(self):
        with patch.object(p, 'audit', return_value=['deliberate concentration mismatch']):
            result = p.submit(fixture_batch(1, 1), 'test')
        self.assertEqual(result['status'], 'rejected')
        self.assertFalse(list(Path(self.temp.name).rglob('protocol.py')))

    def test_timeout_stops_batch_without_false_pass(self):
        result = p.submit(fixture_batch(1, 2), 'test')
        with patch.object(p.subprocess, 'run', side_effect=subprocess.TimeoutExpired('sim', 30)) as call:
            outcome = p.simulate_batch(result['batch_id'], 'test')
        self.assertEqual(call.call_count, 1)
        self.assertEqual([r['status'] for r in outcome['runs']], ['timeout', 'not_run'])

    def test_modified_protocol_cannot_reuse_simulation(self):
        result = p.submit(fixture_batch(1, 1), 'test')
        protocol = Path(result['manifest']).parent / 'run-001/protocol.py'
        protocol.write_text(protocol.read_text() + '\n# modified\n')
        with patch.object(p.subprocess, 'run') as call:
            with self.assertRaises(ValueError):
                p.simulate_batch(result['batch_id'], 'test')
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
