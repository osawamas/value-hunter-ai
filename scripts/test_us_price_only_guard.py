import unittest
from us_price_only_guard import evaluate_budget_entry as check, evaluate_budget_entry_for_sessions as session_check


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


    def test_session_boundaries_reject_stale_fallback(self):
        args = dict(expected_previous_date="2026-11-16",
                    expected_current_date="2026-11-17", **self.flags)
        self.assertEqual(session_check(self.old, self.new, **args),
                         (True, "entered_100_share_budget"))
        stale = {**self.old, "date": "2026-11-13"}
        self.assertEqual(session_check(stale, self.new, **args),
                         (False, "session_close_missing_or_stale"))
        self.assertEqual(session_check(self.old, None, **args),
                         (False, "invalid_trade_dates"))

    def test_session_calendar_not_assumed_consecutive(self):
        friday = {**self.old, "date": "2026-11-13"}
        self.assertTrue(session_check(friday, self.new,
            expected_previous_date="2026-11-13",
            expected_current_date="2026-11-17", **self.flags)[0])
        self.assertFalse(session_check(self.old, self.new,
            expected_previous_date="2026-11-17",
            expected_current_date="2026-11-16", **self.flags)[0])

if __name__ == "__main__":
    unittest.main()
