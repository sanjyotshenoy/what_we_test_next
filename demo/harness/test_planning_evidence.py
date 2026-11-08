import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from gxl_paperclip import PaperclipClient

from demo.harness import planning_evidence as evidence

CLIENT_SPEC = PaperclipClient(auth=Mock(), base_url='https://example.invalid')


class EvidenceTests(unittest.TestCase):
    def test_malformed_context_arguments_are_actionable_without_echoing_values(self):
        with patch('demo.harness.budget.consume'), patch.object(evidence, 'planning_context'):
            with self.assertRaisesRegex(ValueError, r'none; use \{\}') as caught:
                evidence.run('planning_context', {'': {'private': 'do-not-echo'}}, 'test')
            self.assertNotIn('do-not-echo', str(caught.exception))

    def test_invalid_requests_do_not_reach_service(self):
        with patch.object(evidence, 'client') as client:
            for args in [('../private/credentials.json', 1, 10), ('PMC1', 1, 100), ('PMC1', 0, 2)]:
                with self.assertRaises(ValueError):
                    evidence.literature_read(*args)
            with self.assertRaises(ValueError):
                evidence.literature_search('query', 100)
            client.assert_not_called()

    def test_only_returned_source_lines_are_citable(self):
        client = Mock(spec=CLIENT_SPEC)
        client.papers.cat.return_value = SimpleNamespace(exit_code=0, output=json.dumps({'document_id':'PMC1', 'doi':'example'}))
        client.execute.return_value = SimpleNamespace(exit_code=0, output='L1: outside\nL4: actual evidence\nL5: more evidence\nL99: outside\nserver footer')
        with patch.object(evidence, 'client', return_value=client):
            result = evidence.literature_read('PMC1', 4, 6)
        self.assertEqual(result['passage'], 'L4: actual evidence\nL5: more evidence')
        self.assertIn('PMC1:L4-L5:', result['evidence_id'])
        self.assertTrue(result['truncated'])

    def test_failed_read_does_not_become_evidence(self):
        client = Mock(spec=CLIENT_SPEC)
        client.papers.cat.return_value = SimpleNamespace(exit_code=1, output='error')
        with patch.object(evidence, 'client', return_value=client):
            with self.assertRaises(ValueError):
                evidence.literature_read('PMC1')

    def test_search_excludes_generated_summaries(self):
        client = Mock()
        client.search.return_value = SimpleNamespace(exit_code=0, papers=[{'document_id':'PMC1','tldr':'uncited claim','title':'Paper'}], result_id='s_1')
        with patch.object(evidence, 'client', return_value=client):
            result = evidence.literature_search('query')
        self.assertNotIn('tldr', result['papers'][0])

    def test_benchmark_and_session_traversal_fail_before_tools(self):
        with patch.dict(os.environ, {'HARNESS_EVIDENCE_MODE':'benchmark'}):
            with self.assertRaises(ValueError):
                evidence.run('planning_context', {}, 'test')
        with self.assertRaises(ValueError):
            evidence.run('planning_context', {}, '../test')

    def test_artifact_is_scoped_to_session(self):
        with TemporaryDirectory() as d, patch.object(evidence, 'OUT', Path(d)), patch.dict(evidence.TOOLS, {'fixture': lambda: {'evidence_id':'paper:fixture'}}):
            evidence.run('fixture', {}, 'session1')
            records = list((Path(d)/'session1').glob('*.json'))
            self.assertEqual(len(records), 1)
            self.assertEqual(json.loads(records[0].read_text())['result']['evidence_id'], 'paper:fixture')


if __name__ == '__main__':
    unittest.main()
