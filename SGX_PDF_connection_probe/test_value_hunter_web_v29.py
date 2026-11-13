import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from value_hunter_web_v29 import build, SYMBOLS


def fixture():
    return {"schema_version": "value_hunter_sgx_v28",
            "generated_at_utc": "2026-11-13T00:00:00+00:00",
            "records": [{"symbol": symbol, "ranking_eligible": False,
                         "exclusion_reasons": ["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"],
                         "price_sgd": None, "financial_source_url": "https://example.org/docs.pdf"}
                        for symbol in SYMBOLS]}


class TestPublisher(unittest.TestCase):
    def test_valid(self):
        out = build(fixture(), datetime(2026, 11, 13, tzinfo=timezone.utc))
        self.assertEqual(len(out["records"]), 3)
        self.assertEqual(out["ranking_eligible_count"], 0)
        self.assertIsNone(out["records"][0]["price_sgd"])

    def test_missing_symbol(self):
        sample = fixture()
        sample["records"].pop()
        with self.assertRaises(ValueError):
            build(sample)

    def test_duplicate_symbol(self):
        sample = fixture()
        sample["records"][1]["symbol"] = "S68"
        with self.assertRaises(ValueError):
            build(sample)

    def test_wrong_schema(self):
        sample = fixture()
        sample["schema_version"] = "v1"
        with self.assertRaises(ValueError):
            build(sample)

    def test_unverified_ranking_not_promoted(self):
        sample = fixture()
        sample["records"][0]["ranking_eligible"] = True
        with self.assertRaises(ValueError):
            build(sample)

    def test_missing_reason(self):
        sample = fixture()
        sample["records"][0]["exclusion_reasons"] = []
        with self.assertRaises(ValueError):
            build(sample)

    def test_url_sanitization(self):
        sample = fixture()
        sample["records"][0]["quote_url"] = "javascript:alert(1)"
        sample["records"][0]["audit_source_url"] = "https://example.org/fy2025.pdf"
        sample["records"][0]["audit_pages_by_metric"] = {"revenue": [4]}
        out = build(sample)
        self.assertIsNone(out["records"][0]["quote_url"])
        self.assertEqual(out["records"][0]["audit_source_url"], "https://example.org/fy2025.pdf")
        self.assertEqual(out["records"][0]["audit_pages_by_metric"], {"revenue": [4]})
        self.assertEqual(out["records"][0]["financial_source_url"], "https://example.org/docs.pdf")


if __name__ == "__main__":
    unittest.main()
