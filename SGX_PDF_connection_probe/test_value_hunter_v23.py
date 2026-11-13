import unittest
from value_hunter_v23 import parse_s20_pdf_text

class TestS20(unittest.TestCase):
    SAMPLE=('15. Share capital Issued and fully paid ordinary shares (including treasury shares) '
            'At 30 June 487,930,935 16. Treasury shares At 30 June (3,108,109) '
            'As at 30 June 2026, the Company held 3,108,109 treasury shares which represents 0.6% '
            'of the total number of issued shares 484,822,826 (excluding treasury shares).')
    def test_reconcile(self):
        x=parse_s20_pdf_text(self.SAMPLE)
        self.assertEqual(x['shares_outstanding'],484822826)
        self.assertEqual(x['issued_shares_including_treasury']-x['treasury_shares'],x['shares_outstanding'])
    def test_missing_net_label(self):
        with self.assertRaises(ValueError):parse_s20_pdf_text(self.SAMPLE.replace('(excluding treasury shares)',''))
    def test_wrong_net(self):
        with self.assertRaises(ValueError):parse_s20_pdf_text(self.SAMPLE.replace('484,822,826','484,822,825'))
    def test_missing_gross(self):
        with self.assertRaises(ValueError):parse_s20_pdf_text(self.SAMPLE.replace('487,930,935','487,930,934'))

if __name__=='__main__':unittest.main()
