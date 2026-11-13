import unittest
from value_hunter_v26 import audit

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.fin = {'records': [
            {'symbol':'G13','metrics':{'revenue':{'2025':{'value':2452053}},
                                       'operating_profit':{'2025':{'value':506609}},
                                       'attributable_profit':{'2025':{'value':390346}}}},
            {'symbol':'S20','metrics':{'revenue':{'2025':{'value':623300}},
                                       'attributable_profit':{'2025':{'value':-249133}}}},
            {'symbol':'S68','metrics':{}}]}
    def test_matches_and_no_ranking(self):
        result = audit(self.fin, {'records':[]})
        self.assertEqual(result['ranking_eligible_count'],0)
        self.assertTrue(result['records'][1]['cross_document_subset_matched'])
        self.assertTrue(result['records'][2]['cross_document_subset_matched'])
        self.assertTrue(all(not r['investment_ranking_eligible'] for r in result['records']))
    def test_mismatch_blocks(self):
        self.fin['records'][0]['metrics']['revenue']['2025']['value']=0
        result=audit(self.fin,{'records':[]})
        self.assertEqual(result['records'][1]['checks'][0]['status'],'MISMATCH')
        self.assertFalse(result['records'][1]['cross_document_subset_matched'])
    def test_missing_blocks(self):
        del self.fin['records'][0]['metrics']['operating_profit']
        result=audit(self.fin,{'records':[]})
        self.assertEqual(result['records'][1]['checks'][1]['status'],'MISSING')
    def test_s68_not_verified(self):
        result=audit(self.fin,{'records':[]})
        self.assertEqual(result['records'][0]['checks'][0]['status'],'NO_SECOND_DOCUMENT_REFERENCE')

if __name__=='__main__': unittest.main()
