import unittest
from financial_audit_v10 import audit

class TestAudit(unittest.TestCase):
    def payload(self, lines):
        return {'document':{'document_id':'TEST','expected_fiscal_year':2026}, 'candidates':[{'page':p,'line':line} for p,line in lines]}
    def test_balances_both_years(self):
        result = audit(self.payload([(13,'Total assets 4,547,470 4,143,988'),(13,'Total liabilities 2,184,488 1,944,067'),(13,'Total equity 2,362,982 2,199,921')]))
        self.assertEqual(result['balance_consistent_tables'], 1)
        self.assertEqual(result['balance_sheet_tables'][0]['scope'], 'unclassified')
    def test_mismatch_not_verified(self):
        result = audit(self.payload([(13,'Total assets 100 90'),(13,'Total liabilities 30 20'),(13,'Total equity 60 70')]))
        self.assertEqual(result['balance_sheet_tables'][0]['status'], 'arithmetic_mismatch')
    def test_two_tables_not_conflated(self):
        lines=[]
        for p, a, l, e in [(13,'100 90','30 20','70 70'),(19,'200 180','60 50','140 130')]:
            lines.extend([(p,'Total assets '+a),(p,'Total liabilities '+l),(p,'Total equity '+e)])
        self.assertEqual(audit(self.payload(lines))['balance_consistent_tables'], 2)
    def test_income_four_columns(self):
        result = audit(self.payload([(9,'823,286 688,398 19.6 Operating revenue 1,559,469 1,370,625 13.8')]))
        self.assertEqual(result['income_statement_candidates'][0]['full_year_columns'], [1559469,1370625])
    def test_no_false_certification(self):
        self.assertEqual(audit(self.payload([]))['financial_validation'], 'NOT_VERIFIED')

if __name__ == '__main__': unittest.main()
