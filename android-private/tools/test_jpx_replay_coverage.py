import unittest
from jpx_replay_coverage import reconcile


class ReplayTests(unittest.TestCase):
    def fixture(self):
        return dict(
            previous_date="2026-11-16", latest_date="2026-11-17",
            previous_closes={"1001": "1001", "1002": "2000", "1003": "1000"},
            latest_closes={"1001": "999", "1002": "1800", "1003": "900"},
            financial_codes=["1003"],
            listed_codes=["1001", "1002", "1003", "1004"],
            split_verified_free_codes=["1002"],
            dividend_verified_free_codes=["1002"],
        )

    def test_distinct_candidates_do_not_double_count_reasons(self):
        data = self.fixture()
        data["previous_closes"]["1002"] = "1001"
        data["latest_closes"]["1002"] = "900"
        result = reconcile(data)
        self.assertEqual(result["budget_entries"], 2)
        self.assertEqual(result["rapid_moves_verified"], 1)
        self.assertEqual(result["budget_and_rapid_overlap"], 1)
        self.assertEqual(result["distinct_reference_candidate_codes"], 2)
        self.assertEqual(result["distinct_reference_candidate_market_percent"], "50.00")
        self.assertIsNone(result["new_notifications"])

    def test_unverified_rapid_is_not_counted_as_candidate(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "900"
        result = reconcile(data)
        self.assertEqual(result["rapid_moves_held_unverified"], 1)
        self.assertEqual(result["distinct_reference_candidate_codes"], 2)

    def test_overlap_and_event_gates(self):
        result = reconcile(self.fixture())
        self.assertEqual(result["price_only_assessable"], 2)
        self.assertEqual(result["paired_financial_overlap"], 1)
        self.assertEqual(result["budget_entries"], 1)
        self.assertEqual(result["rapid_moves_verified"], 1)
        self.assertIsNone(result["new_notifications"])

    def test_market_coverage_counts_are_disjoint(self):
        result = reconcile(self.fixture())
        self.assertEqual(result["paired_financial_overlap"], 1)
        self.assertEqual(result["price_only_assessable"], 2)
        self.assertEqual(result["paired_financial_and_price_only_union"], 3)
        self.assertEqual(result["paired_financial_coverage_percent"], "25.00")
        self.assertEqual(result["paired_total_market_coverage_percent"], "75.00")

    def test_financial_registration_outside_paired_closes_counts_in_union(self):
        data = self.fixture()
        data["financial_codes"] = ["1003", "1004"]
        result = reconcile(data)
        self.assertEqual(result["paired_financial_and_price_only_union"], 3)
        self.assertEqual(result["registered_financial_or_price_only_union"], 4)
        self.assertEqual(result["registered_financial_or_price_only_market_percent"], "100.00")

    def test_unverified_dividend_holds_rapid(self):
        data = self.fixture()
        data["dividend_verified_free_codes"] = []
        self.assertEqual(reconcile(data)["rapid_moves_verified"], 0)

    def test_nonrapid_unverified_not_counted_as_held(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "1000"
        self.assertEqual(reconcile(data)["rapid_moves_held_unverified"], 0)

    def test_rapid_unverified_is_held(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "900"
        self.assertEqual(reconcile(data)["rapid_moves_held_unverified"], 1)

    def test_missing_session_counted_separately(self):
        data = self.fixture()
        del data["latest_closes"]["1001"]
        result = reconcile(data)
        self.assertEqual(result["missing_latest_close"], 1)
        self.assertEqual(result["paired_closes"], 2)
        self.assertEqual(result["price_only_assessable"], 1)
        self.assertEqual(result["budget_entries"], 0)

    def test_event_hold_reasons_are_not_double_counted_in_total(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "900"
        result = reconcile(data)
        self.assertEqual(result["rapid_moves_held_unverified"], 1)
        self.assertEqual(result["rapid_moves_held_split_unverified"], 1)
        self.assertEqual(result["rapid_moves_held_dividend_unverified"], 1)
        self.assertEqual(result["rapid_moves_held_both_unverified"], 1)

    def test_malformed_decimal_fails_closed(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "not-a-price"
        with self.assertRaises(ValueError):
            reconcile(data)

    def test_same_day_rejected(self):
        data = self.fixture()
        data["previous_date"] = data["latest_date"]
        with self.assertRaises(ValueError):
            reconcile(data)

    def test_nonfinite_price_rejected(self):
        data = self.fixture()
        data["latest_closes"]["1001"] = "NaN"
        with self.assertRaises(ValueError):
            reconcile(data)

    def test_aggregate_financial_count_rejected(self):
        data = self.fixture()
        data["financial_codes"] = 4194
        with self.assertRaises(ValueError):
            reconcile(data)


if __name__ == "__main__":
    unittest.main()
