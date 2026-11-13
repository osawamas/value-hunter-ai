import unittest
from value_hunter_shares_v21 import SHARES


class S63SharesTests(unittest.TestCase):
    def test_june_2026_arithmetic(self):
        result = SHARES["S63"]
        self.assertEqual(3_122_495_197 - 3_190_209, result["shares_outstanding"])
        self.assertEqual(result["as_of_date"], "2026-06-30")
        self.assertEqual(result["share_count_basis"], "issued_excluding_treasury")

    def test_not_marked_live_verified(self):
        result = SHARES["S63"]
        self.assertEqual(result["verification_status"], "DOCUMENTED_SNAPSHOT_NOT_LIVE_VERIFIED")
        self.assertTrue(result["source_url"].startswith("https://links.sgx.com/"))
        self.assertIn("later share repurchases", result["source_detail"])


if __name__ == "__main__":
    unittest.main()
