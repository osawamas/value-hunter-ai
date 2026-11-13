import unittest
from value_hunter_v24 import parse_s20_shares
class TestS20V24(unittest.TestCase):
    def test_multiline_reconciliation(self):
        s='''15. Share capital\nIssued and fully paid ordinary shares (including treasury shares)\nAt 30 June 2026\n487,930,935\n16. Treasury shares\nAt 30 June 2026\n3,108,109\nAs at 30 June 2026 the total number of issued shares\n484,822,826 (excluding treasury shares).'''
        x,a=parse_s20_shares(s)
        self.assertIsNotNone(x,a)
        self.assertEqual(x['shares_outstanding'],484822826)
        self.assertEqual(a['status'],'PDF_THREE_WAY_RECONCILED')
    def test_arithmetic_without_net(self):
        s='''Share capital\nIssued shares\n487,930,935\nTreasury shares\n3,108,109'''
        x,a=parse_s20_shares(s)
        self.assertEqual(x['shares_outstanding'],484822826)
        self.assertEqual(a['status'],'PDF_GROSS_MINUS_TREASURY_ONLY')
    def test_conflicting_net(self):
        s='''Issued shares\n487,930,935\nTreasury shares\n3,108,109\n484,822,825 (excluding treasury shares)'''
        x,a=parse_s20_shares(s)
        self.assertIsNone(x)
    def test_no_evidence(self):
        x,a=parse_s20_shares('Revenue 487,930,935\nProfit 3,108,109')
        self.assertIsNone(x)
if __name__=='__main__':unittest.main()
