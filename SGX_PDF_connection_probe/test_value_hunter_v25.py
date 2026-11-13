import unittest
from value_hunter_v25 import parse_s20_shares

NARRATIVE = '''As at 30 June 2026, the Company held 3,108,109 treasury shares (31 December 2025: 3,346,495)
which represents 0.6% (31 December 2025: 0.7%) of the total number of issued shares 484,822,826
(31 December 2025: 468,881,319) (excluding treasury shares).'''
NOTE = '''15. Share capital Group and Company 2026 2025 Number of shares $'000 Number of shares $'000
Issued and fully paid ordinary shares (including treasury shares)
At 30 June/31 December 487,930,935 741,218 472,227,814 714,716
16. Treasury shares'''

class DateAnchoringTests(unittest.TestCase):
    def test_current_date_correct(self):
        shares,audit=parse_s20_shares(NOTE+'\n'+NARRATIVE)
        self.assertEqual(shares['shares_outstanding'],484822826)
        self.assertEqual(shares['treasury_shares'],3108109)
        self.assertEqual(shares['issued_shares_including_treasury'],487930935)
        self.assertEqual(shares['as_of_date'],'2026-06-30')
        self.assertEqual(audit['status'],'DATE_ANCHORED_RECONCILED')
    def test_prior_date_never_selected(self):
        shares,audit=parse_s20_shares(NOTE+'\n'+NARRATIVE)
        self.assertNotEqual(shares['shares_outstanding'],468881319)
        self.assertEqual(audit['dates_found'],['2025-12-31','2026-06-30'])
    def test_missing_target_date_fails_closed(self):
        shares,audit=parse_s20_shares(NARRATIVE,target_date='2026-09-30')
        self.assertIsNone(shares)
        self.assertEqual(audit['status'],'TARGET_DATE_MISSING')
    def test_no_date_no_accept(self):
        shares,audit=parse_s20_shares('484,822,826 3,108,109 468,881,319')
        self.assertIsNone(shares)
    def test_without_gross_note_downgrades(self):
        shares,audit=parse_s20_shares(NARRATIVE)
        self.assertEqual(shares['shares_outstanding'],484822826)
        self.assertEqual(audit['status'],'DATE_ANCHORED_NET_AND_TREASURY_ONLY')
    def test_conflicting_current_values_rejected(self):
        altered=NARRATIVE.replace('484,822,826','484,822,825')
        shares,audit=parse_s20_shares(NARRATIVE+'\n'+altered)
        self.assertIsNone(shares)
        self.assertEqual(audit['status'],'CONFLICTING_TARGET_DATE_VALUES')

if __name__=='__main__': unittest.main()
