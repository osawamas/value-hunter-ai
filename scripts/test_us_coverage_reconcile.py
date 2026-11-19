import unittest
from us_coverage_reconcile import reconcile_us_coverage


class ReconcileTests(unittest.TestCase):
    def test_overlap_is_excluded_and_denominator_is_full_listing(self):
        listed = {"NYSE": {"A", "B", "C", "D"}, "Nasdaq": {"X", "Y"}}
        paired = {"NYSE": {"A", "B", "C"}, "Nasdaq": {"X"}}
        financial = {"NYSE": {"A", "D"}, "Nasdaq": {"Y"}}
        candidates = {"NYSE": {"A", "B"}, "Nasdaq": {"X"}}
        out = reconcile_us_coverage(listed, paired, financial, candidates)
        self.assertEqual(out["NYSE"]["price_only_possible_before_provenance"], 2)
        self.assertEqual(out["NYSE"]["price_only_coverage_pct"], 50.0)
        self.assertEqual(out["NYSE"]["crossings_before_provenance"], 1)
        self.assertEqual(out["NYSE"]["crossings_excluded_financial"], 1)
        self.assertEqual(out["Nasdaq"]["paired_coverage_pct"], 50.0)
        self.assertIsNone(out["NYSE"]["notification_verified"])

    def test_rejects_noncanonical_whitespace_symbols(self):
        listed = {"NYSE": {"ABC "}, "Nasdaq": {"XYZ"}}
        paired = {"NYSE": {"ABC "}, "Nasdaq": {"XYZ"}}
        financial = {"NYSE": set(), "Nasdaq": set()}
        candidates = {"NYSE": set(), "Nasdaq": set()}
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            reconcile_us_coverage(listed, paired, financial, candidates)

    def test_rejects_duplicate_listing_symbol_across_exchanges(self):
        listed = {"NYSE": {"SHARED", "A"}, "Nasdaq": {"SHARED", "B"}}
        paired = {"NYSE": {"SHARED"}, "Nasdaq": {"SHARED"}}
        financial = {"NYSE": set(), "Nasdaq": set()}
        candidates = {"NYSE": set(), "Nasdaq": set()}
        with self.assertRaisesRegex(ValueError, "duplicate symbol"):
            reconcile_us_coverage(listed, paired, financial, candidates)

    def test_rejects_aggregated_counts_and_wrong_market(self):
        good = {"NYSE": {"A"}, "Nasdaq": {"B"}}
        with self.assertRaises(ValueError):
            reconcile_us_coverage(good, {"NYSE": 1, "Nasdaq": 1}, good, good)
        with self.assertRaises(ValueError):
            reconcile_us_coverage(good, {"NYSE": {"B"}, "Nasdaq": {"B"}}, good, good)
        with self.assertRaises(ValueError):
            reconcile_us_coverage(good, good, good, {"NYSE": {"C"}, "Nasdaq": set()})


if __name__ == "__main__":
    unittest.main()
