import unittest
from us_price_only_guard import evaluate_budget_entry as check, evaluate_budget_entry_for_sessions as session_check, evaluate_verified_budget_entry as verified_check


class PriceOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.old = {"date": "2026-11-16", "close_usd": "8", "usd_jpy": "150"}
        self.new = {"date": "2026-11-17", "close_usd": "6", "usd_jpy": "150"}
        self.flags = dict(ordinary_share_verified=True, financials_verified=False,
                          corporate_actions_verified=True, source_verified=True)

    def test_boolean_close_or_fx_never_counts_as_number(self):
        for side in ('old', 'new'):
            for field in ('close_usd', 'usd_jpy'):
                for bad in (True, False):
                    with self.subTest(side=side, field=field, bad=bad):
                        old, new = dict(self.old), dict(self.new)
                        (old if side == 'old' else new)[field] = bad
                        self.assertEqual(check(old, new, **self.flags),
                                         (False, 'invalid_close_or_fx'))

    def test_noncanonical_dates_rejected(self):
        args = dict(expected_previous_date='2026-11-16', expected_current_date='2026-11-17', **self.flags)
        for bad in ('2026-11-7', '2026-W47-2', '2026-11-17T00:00:00', '20261117'):
            with self.subTest(bad=bad):
                self.assertEqual(session_check(self.old, {**self.new, 'date': bad}, **args),
                                 (False, 'invalid_trade_dates'))
                self.assertEqual(session_check(self.old, self.new,
                    **{**args, 'expected_current_date': bad}), (False, 'invalid_trade_dates'))

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

    def test_bad_prices(self):
        self.assertFalse(check(self.old, {**self.new, "close_usd": "NaN"}, **self.flags)[0])

    def test_malformed_numeric_strings_do_not_create_candidates(self):
        for field in ("close_usd", "usd_jpy"):
            for value in ("1_50", " 150", "150 ", "1e2", "+150", "１５０"):
                with self.subTest(field=field, value=value):
                    self.assertEqual(check(self.old, {**self.new, field: value}, **self.flags),
                                     (False, "invalid_close_or_fx"))

    def test_exact_budget_boundary(self):
        previous = {**self.old, "close_usd": "10.0001", "usd_jpy": "100"}
        for value, crossed in (("9.9999", True), ("10.0000", True), ("10.0001", False)):
            observation = {**self.new, "close_usd": value, "usd_jpy": "100"}
            self.assertEqual(check(previous, observation, **self.flags)[0], crossed)
            self.assertFalse(check({**previous, "close_usd": value},
                                   {**observation, "close_usd": "10.0001"}, **self.flags)[0])

    def test_subcent_precision_cannot_round_overbudget_into_budget(self):
        previous = {**self.old, "close_usd": "11", "usd_jpy": "100"}
        for value, crossed in (("10.00000000000000000000000000001", False),
                               ("9.99999999999999999999999999999", True)):
            with self.subTest(value=value):
                current = {**self.new, "close_usd": value, "usd_jpy": "100"}
                self.assertEqual(check(previous, current, **self.flags)[0], crossed)

    def test_budget_crossing_does_not_depend_on_ambient_decimal_precision(self):
        from decimal import localcontext
        previous = {**self.old, "close_usd": "10.0001", "usd_jpy": "100"}
        current = {**self.new, "close_usd": "10", "usd_jpy": "100"}
        with localcontext() as ctx:
            ctx.prec = 5
            self.assertEqual(check(previous, current, **self.flags),
                             (True, "entered_100_share_budget"))

    def test_unrepresentable_cost_fails_closed(self):
        from decimal import Decimal
        current = {**self.new, "close_usd": Decimal("1e999999"), "usd_jpy": "100"}
        self.assertEqual(check(self.old, current, **self.flags),
                         (False, "invalid_close_or_fx"))

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
        evidence = {"symbol": "ABC", "exchange": "Nasdaq", "close_venue": "Nasdaq",
                    "independent_raw_close_verified": True}
        old = {**self.old, **evidence, "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.old["date"], "close_source": "exchange:old",
               "fx_source": "fixing:old"}
        new = {**self.new, **evidence, "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.new["date"], "close_source": "exchange:new",
               "fx_source": "fixing:new"}
        args = dict(expected_previous_date=self.old["date"],
                    expected_current_date=self.new["date"], expected_symbol="ABC",
                    expected_exchange="Nasdaq", **self.flags)
        self.assertTrue(verified_check(old, new, **args)[0])
        for field, bad, reason in (
            ("price_basis", "split_adjusted", "raw_close_basis_unverified"),
            ("price_basis", None, "raw_close_basis_unverified"),
            ("close_venue", "NYSE", "close_venue_mismatch"),
            ("independent_raw_close_verified", None, "independent_raw_close_unverified"),
            ("independent_raw_close_verified", "true", "independent_raw_close_unverified"),
            ("fx_date", self.old["date"], "fx_session_mismatch"),
            ("close_source", "", "missing_source_reference"),
            ("fx_source", None, "missing_source_reference"),
        ):
            with self.subTest(field=field, bad=bad):
                self.assertEqual(verified_check(old, {**new, field: bad}, **args), (False, reason))
                if field != "fx_date":
                    self.assertEqual(verified_check({**old, field: bad}, new, **args), (False, reason))
        self.assertFalse(verified_check(old, {**new, "date": "2026-11-18",
                         "fx_date": "2026-11-18"}, **args)[0])

    def test_verified_fallback_rejects_wrong_ticker_or_exchange(self):
        evidence = {"symbol": "ABC", "exchange": "Nasdaq", "close_venue": "Nasdaq",
                    "independent_raw_close_verified": True}
        old = {**self.old, **evidence,
               "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.old["date"], "close_source": "source:old",
               "fx_source": "fx:old"}
        new = {**self.new, **evidence,
               "price_basis": "raw_unadjusted_regular_session",
               "fx_date": self.new["date"], "close_source": "source:new",
               "fx_source": "fx:new"}
        args = dict(expected_previous_date=self.old["date"],
                    expected_current_date=self.new["date"],
                    expected_symbol="ABC", expected_exchange="Nasdaq", **self.flags)
        self.assertEqual(verified_check(old, new, **args),
                         (True, "entered_100_share_budget"))
        for changed in ({"symbol": "XYZ"}, {"exchange": "NYSE"},
                        {"symbol": None}, {"exchange": None}):
            with self.subTest(changed=changed):
                self.assertEqual(verified_check(old, {**new, **changed}, **args),
                                 (False, "fallback_identity_mismatch"))
                self.assertEqual(verified_check({**old, **changed}, new, **args),
                                 (False, "fallback_identity_mismatch"))
        self.assertEqual(verified_check(old, new,
                         **{**args, "expected_exchange": "AMEX"}),
                         (False, "invalid_expected_identity"))
        self.assertEqual(verified_check(old, new,
                         **{**args, "expected_symbol": None}),
                         (False, "missing_expected_identity"))
        self.assertEqual(verified_check(old, new,
                         **{**args, "expected_symbol": None, "expected_exchange": None}),
                         (False, "missing_expected_identity"))

    def test_fx_only_crossing_and_reverse_direction(self):
        """Each session must use its own USD/JPY; reverse crossing is not entry."""
        args = dict(expected_previous_date="2026-11-16",
                    expected_current_date="2026-11-17", **self.flags)
        old = {**self.old, "close_usd": "7", "usd_jpy": "150"}
        entered = {**self.new, "close_usd": "7", "usd_jpy": "140"}
        self.assertEqual(session_check(old, entered, **args),
                         (True, "entered_100_share_budget"))
        self.assertEqual(session_check(entered | {"date": old["date"]},
                                       old | {"date": entered["date"]}, **args),
                         (False, "no_budget_crossing"))
        self.assertEqual(session_check(old, {**entered, "usd_jpy": "150"}, **args),
                         (False, "no_budget_crossing"))

    def test_price_only_rise_cannot_be_budget_entry(self):
        old = {**self.old, "close_usd": "6", "usd_jpy": "150"}
        new = {**self.new, "close_usd": "8", "usd_jpy": "150"}
        self.assertEqual(check(old, new, **self.flags),
                         (False, "no_budget_crossing"))

if __name__ == "__main__":
    unittest.main()
