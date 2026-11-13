import unittest
from copy import deepcopy
from datetime import datetime, timezone
from value_hunter_quality_v33 import audit_record, inspect_feed

NOW = datetime(2026, 11, 13, 15, 0, tzinfo=timezone.utc)

def record():
    return {"symbol": "G13", "ranking_eligible": False,
            "exclusion_reasons": ["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"],
            "price_sgd": 0.575, "shares_outstanding": 12_000_000_000,
            "market_cap_sgd": 6_900_000_000, "per_reference": 17.6767,
            "pbr_reference_unverified": 0.85, "pbr_verified": None,
            "attributable_profit_sgd_thousands": 390346,
            "quote_timestamp_utc": "2026-11-13T13:00:00+00:00",
            "shares_as_of_date": "2026-10-01"}

def feed():
    return {"schema_version": "value_hunter_web_v29", "ranking_enabled": False,
            "ranking_eligible_count": 0, "updated_at_utc": "2026-11-13T14:00:00+00:00",
            "records": [record()]}

class QualityTests(unittest.TestCase):
    def test_good_arithmetic(self):
        result = audit_record(record(), NOW)
        self.assertEqual(result["quote_freshness"], "RECENT")
        self.assertEqual(result["market_cap_sgd"], 6_900_000_000)
        self.assertEqual(result["per_reference"], 17.6767)

    def test_cap_mismatch_suppresses_derived(self):
        r = record()
        r["market_cap_sgd"] = 5_000_000_000
        out = audit_record(r, NOW)
        self.assertIsNone(out["market_cap_sgd"])
        self.assertIsNone(out["per_reference"])
        self.assertIsNone(out["pbr_reference_unverified"])
        self.assertIn("MARKET_CAP_ARITHMETIC_MISMATCH", out["quality_flags"])

    def test_per_mismatch(self):
        r = record()
        r["per_reference"] = 3
        out = audit_record(r, NOW)
        self.assertIsNone(out["per_reference"])
        self.assertIn("PER_ARITHMETIC_MISMATCH_OR_INVALID", out["quality_flags"])

    def test_stale_quote(self):
        r = record()
        r["quote_timestamp_utc"] = "2026-01-01T00:00:00Z"
        self.assertEqual(audit_record(r, NOW)["quote_freshness"], "STALE")

    def test_stale_shares(self):
        r = record()
        r["shares_as_of_date"] = "2025-01-01"
        self.assertEqual(audit_record(r, NOW)["share_freshness"], "STALE")

    def test_missing_quote(self):
        r = record()
        r["price_sgd"] = None
        r["market_cap_sgd"] = None
        r["per_reference"] = None
        r["pbr_reference_unverified"] = None
        result = audit_record(r, NOW)
        self.assertEqual(result["quote_freshness"], "MISSING")

    def test_nonfinite_invalid(self):
        r = record()
        r["price_sgd"] = float("nan")
        self.assertIsNone(audit_record(r, NOW)["market_cap_sgd"])

    def test_no_ranking_promotion(self):
        r = record()
        r["ranking_eligible"] = True
        with self.assertRaises(ValueError):
            audit_record(r, NOW)

    def test_full_feed_quality(self):
        result = inspect_feed(feed(), NOW)
        self.assertEqual(result["quality_counts"]["issuers"], 1)
        self.assertFalse(result["ranking_enabled"])
        self.assertEqual(result["ranking_eligible_count"], 0)

    def test_duplicate_blocks(self):
        value = feed()
        value["records"].append(deepcopy(value["records"][0]))
        with self.assertRaises(ValueError):
            inspect_feed(value, NOW)

    def test_invalid_timestamp_blocks(self):
        value = feed()
        value["updated_at_utc"] = None
        with self.assertRaises(ValueError):
            inspect_feed(value, NOW)

if __name__ == "__main__":
    unittest.main()
