import unittest
from us_price_only_guard import evaluate_budget_entry as check


class PriceOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.old = {"date": "2026-11-16", "close_usd": "8", "usd_jpy": "150"}
        self.new = {"date": "2026-11-17", "close_usd": "6", "usd_jpy": "150"}
        self.flags = dict(ordinary_share_verified=True, financials_verified=False,
                          corporate_actions_verified=True, source_verified=True)

    def test_crossing(self):
        self.assertEqual(check(self.old, self.new, **self.flags),
                         (True, "entered_100_share_budget"))

    def test_stale_blocks(self):
        self.assertFalse(check(self.old, self.new, stale_cache=True, **self.flags)[0])

    def test_financials_block(self):
        self.assertFalse(check(self.old, self.new, **{**self.flags, "financials_verified": True})[0])

    def test_fx_day_matters(self):
        old = {**self.old, "close_usd": "6", "usd_jpy": "140"}
        self.assertFalse(check(old, self.new, **self.flags)[0])

    def test_missing_second_day(self):
        self.assertFalse(check(self.old, None, **self.flags)[0])

    def test_bad_prices(self):
        self.assertFalse(check(self.old, {**self.new, "close_usd": "NaN"}, **self.flags)[0])


if __name__ == "__main__":
    unittest.main()
