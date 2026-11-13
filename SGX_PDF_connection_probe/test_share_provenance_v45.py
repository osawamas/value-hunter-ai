"""v45: verify the documented S68 share-count provenance arithmetic."""
import unittest
from value_hunter_shares_v21 import SHARES

class OfficialShareBasisTests(unittest.TestCase):
    def test_s68_2026_snapshot_excludes_treasury(self):
        s = SHARES['S68']
        self.assertEqual(s['as_of_date'], '2026-09-01')
        self.assertEqual(s['issued_shares_including_treasury'], 1071642400)
        self.assertEqual(s['treasury_shares'], 798916)
        self.assertEqual(s['shares_outstanding'], 1070843484)
        self.assertEqual(s['issued_shares_including_treasury'] - s['treasury_shares'], s['shares_outstanding'])
        self.assertEqual(s['share_count_basis'], 'issued_excluding_treasury')
        self.assertTrue(s['source_url'].startswith('https://'))

    def test_g13_2026_basis_remains_unconfirmed(self):
        s=SHARES['G13']
        self.assertNotIn('share_count_basis', s)
        self.assertEqual(s['as_of_date'], '2026-08-14')
        self.assertEqual(s['shares_outstanding'], 12063642274)

if __name__ == '__main__':
    unittest.main()
