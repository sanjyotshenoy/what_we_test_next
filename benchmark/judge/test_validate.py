import copy,json,unittest
from .validate import OUT,validate

class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.packet=json.loads((OUT/'calibration/packets/d3a9b5e7.json').read_text())
        self.grade=json.loads((OUT/'calibration/grades/d3a9b5e7.json').read_text())
    def test_valid_fixture(self):self.assertEqual(validate(self.packet,self.grade),[])
    def test_reject_invented_evidence(self):
        self.grade['axes']['suitability']['response_quotes']=['This quote was not in the response.']
        self.assertTrue(any('nonliteral' in e for e in validate(self.packet,self.grade)))
    def test_reject_boolean_score(self):
        self.grade['axes']['suitability']['score']=True
        self.assertTrue(any('invalid score' in e for e in validate(self.packet,self.grade)))
    def test_reject_mismatched_id(self):
        self.grade['item_id']='some-other-response'
        self.assertIn('item ID mismatch',validate(self.packet,self.grade))
    def test_reject_false_arithmetic(self):
        self.grade['numeric_check'].update(top_uM=10,factor=10,points=3,computed_min_uM=1)
        self.assertIn('judge minimum arithmetic mismatch',validate(self.packet,self.grade))
    def test_reject_nonexistent_evidence_path(self):
        self.grade['axes']['suitability']['input_evidence_paths']=['generator_input.nonexistent']
        self.assertTrue(any('invalid evidence path' in e for e in validate(self.packet,self.grade)))
if __name__=='__main__':unittest.main()
