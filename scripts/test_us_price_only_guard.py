import unittest
from us_price_only_guard import evaluate_budget_entry as check, evaluate_budget_entry_for_sessions as session_check, evaluate_verified_budget_entry as verified_check


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

    def test_unknown_financials_fail_closed(self):
        for status in (None, 0, "", "false"):
            with self.subTest(status=status):
                result = check(self.old, self.new,
                    **{**self.flags, "financials_verified": status})
                self.assertEqual(result, (False, "financials_status_unverified"))

    def test_unverified_flags_fail_closed(self):
        for field in ("ordinary_share_verified", "corporate_actions_verified",
                      "source_verified"):
            for value in (None, 1, "yes"):
                with self.subTest(field=field, value=value):
                    self.assertFalse(check(self.old, self.new,
                        **{**self.flags, field: value})[0])
        self.assertFalse(check(self.old, self.new,
            **{**self.flags, "stale_cache": None})[0])

    def test_fx_day_matters(self):
        old = {**self.old, "close_usd": "6", "usd_jpy": "140"}
        self.assertFalse(check(old, self.new, **self.flags)[0])

    def test_missing_second_day(self):
        self.assertFalse(check(self.old, None, **self.flags)[0])

    def test_boolean_close_and_fx_are_not_numeric_quotes(self):
        for field in ("close_usd", "usd_jpy"):
            for value in (True, False):
                with self.subTest(field=field, value=value):
                    self.assertEqual(check(self.old, {**self.new, field: value}, **self.flags),
                                     (False, "invalid_close_or_fx"))

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


    def test_malformed_observations_fail_closed(self):
        args = dict(expected_previous_date="2026-11-16",
                    expected_current_date="2026-11-17", **self.flags)
        for bad in ("not-a-row", ["2026-11-16"], 42, {"date": None}):
            with self.subTest(bad=bad):
                self.assertFalse(check(bad, self.new, **self.flags)[0])
                self.assertFalse(session_check(bad, self.new, **args)[0])
                self.assertFalse(verified_check(bad, self.new, **args)[0])

    def test_missing_session_is_distinct_from_malformed_row(self):
        args = dict(expected_previous_date="2026-11-16",
                    expected_current_date="2026-11-17", **self.flags)
        for missing_previous, missing_current in ((None, self.new), (self.old, None)):
            self.assertEqual(session_check(missing_previous, missing_current, **args),
                             (False, "invalid_trade_dates"))
        for malformed in ("invalid", 42, ["2026-11-17"]):
            self.assertEqual(session_check(self.old, malformed, **args),
                             (False, "invalid_observation"))

    def test_verified_provenance_gate(self):
        old = {**self.old, "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.old["date"], "close_source": "exchange:old",
               "fx_source": "fixing:old"}
        new = {**self.new, "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.new["date"], "close_source": "exchange:new",
               "fx_source": "fixing:new"}
        args = dict(expected_previous_date=self.old["date"],
                    expected_current_date=self.new["date"], **self.flags)
        self.assertTrue(verified_check(old, new, **args)[0])
        for field, bad, reason in (
            ("price_basis", "split_adjusted", "raw_close_basis_unverified"),
            ("price_basis", None, "raw_close_basis_unverified"),
            ("fx_date", self.old["date"], "fx_session_mismatch"),
            ("close_source", "", "missing_source_reference"),
            ("fx_source", None, "missing_source_reference"),
        ):
            with self.subTest(field=field, bad=bad):
                self.assertEqual(verified_check(old, {**new, field: bad}, **args),
                                 (False, reason))
        self.assertFalse(verified_check(old, {**new, "date": "2026-11-18",
                         "fx_date": "2026-11-18"}, **args)[0])

if __name__ == "__main__":
    unittest.main()
