import copy
import json
import unittest
from pathlib import Path
from consolidated_audit_v13 import verify

ROOT = Path(__file__).resolve().parent / 'fixtures'

class ConsolidatedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = json.loads((ROOT/'S68_FY2026_results_financial_audit.json').read_text())
        cls.h = json.loads((ROOT/'S68_FY2026_results_heading_evidence.json').read_text())

    def test_verified_group_only(self):
        r = verify(self.a, self.h)
        self.assertEqual(r['financial_validation'], 'VERIFIED_CONSOLIDATED_BALANCE_SHEET_ONLY')
        self.assertEqual(r['consolidated_balance_sheet']['page'], 13)
        self.assertEqual(r['consolidated_balance_sheet']['values_thousands_sgd']['assets'], [4547470,4143988])
        self.assertEqual(r['excluded_company_pages'], [19])

    def test_missing_heading_rejected(self):
        h = copy.deepcopy(self.h)
        h['page_scope_evidence'][0]['scope'] = 'unclassified'
        self.assertEqual(verify(self.a,h)['financial_validation'], 'NOT_VERIFIED')

    def test_wrong_year_rejected(self):
        a = copy.deepcopy(self.a)
        a['expected_fiscal_year'] = 2027
        self.assertEqual(verify(a,self.h)['financial_validation'], 'NOT_VERIFIED')

    def test_arithmetic_mismatch_rejected(self):
        a = copy.deepcopy(self.a)
        a['balance_sheet_tables'][0]['values']['assets'][0] += 1
        self.assertEqual(verify(a,self.h)['financial_validation'], 'NOT_VERIFIED')

    def test_unit_missing_rejected(self):
        h = copy.deepcopy(self.h)
        h['page_scope_evidence'][0]['page_start'] = [x for x in h['page_scope_evidence'][0]['page_start'] if "S$'000" not in x['text']]
        self.assertEqual(verify(self.a,h)['financial_validation'], 'NOT_VERIFIED')

    def test_crosscheck_rejected(self):
        h = copy.deepcopy(self.h)
        h['page_scope_evidence'][0]['page_start'] = [dict(x, text=x['text'].replace('4,547,470','4,547,471')) for x in h['page_scope_evidence'][0]['page_start']]
        self.assertEqual(verify(self.a,h)['financial_validation'], 'NOT_VERIFIED')

    def test_no_tables_rejected(self):
        a = copy.deepcopy(self.a)
        a['balance_sheet_tables'] = []
        self.assertEqual(verify(a,self.h)['financial_validation'], 'NOT_VERIFIED')

if __name__ == '__main__':
    unittest.main()
