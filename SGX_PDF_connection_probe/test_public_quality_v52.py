"""v52 public feed never exposes inconsistent treasury arithmetic or PBR."""
import unittest
from datetime import datetime, timezone

from value_hunter_quality_v33 import audit_record

NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)


def sample():
    shares = 1_070_843_484
    price = 10.0
    cap = shares * price
    equity = 2_362_982
    return {
        "symbol": "S68", "ranking_eligible": False,
        "exclusion_reasons": ["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"],
        "shares_outstanding": shares,
        "gross_issued_shares": 1_071_642_400,
        "treasury_shares": 798_916,
        "shares_count_basis": "issued_excluding_treasury",
        "shares_pdf_sha256": "a" * 64,
        "shares_as_of_date": "2026-09-01",
        "price_sgd": price,
        "quote_timestamp_utc": "2026-11-13T00:00:00Z",
        "market_cap_sgd": cap,
        "attributable_profit_sgd_thousands": 698_411,
        "per_reference": round(cap / 698_411_000, 4),
        "parent_equity_sgd_thousands": equity,
        "pbr_reference_unverified": round(cap / (equity * 1000), 4),
        "pbr_verified": None,
    }


class SafetyGateTests(unittest.TestCase):
    def test_valid_treasury_and_pbr(self):
        r = audit_record(sample(), NOW)
        self.assertEqual(r["market_cap_sgd"], 10_708_434_840)
        self.assertIsNotNone(r["pbr_reference_unverified"])
        self.assertEqual(r["quality_flags"], [])

    def test_invalid_treasury_suppresses_all_derived_valuations(self):
        src = sample()
        src["treasury_shares"] += 1
        r = audit_record(src, NOW)
        for key in ("market_cap_sgd", "per_reference", "pbr_reference_unverified"):
            self.assertIsNone(r[key])
        self.assertIn("TREASURY_SHARE_ARITHMETIC_OR_BASIS_MISMATCH", r["exclusion_reasons"])

    def test_incorrect_basis_suppresses_valuations(self):
        src = sample()
        src["shares_count_basis"] = "issued_including_treasury"
        r = audit_record(src, NOW)
        self.assertIsNone(r["market_cap_sgd"])

    def test_bad_pdf_sha_suppresses_valuations(self):
        src = sample()
        src["shares_pdf_sha256"] = "bad"
        r = audit_record(src, NOW)
        self.assertIsNone(r["market_cap_sgd"])
        self.assertIn("SHARE_SOURCE_PDF_SHA256_INVALID", r["quality_flags"])

    def test_incorrect_pbr_denominator_does_not_change_valid_per(self):
        src = sample()
        src["parent_equity_sgd_thousands"] = 1_000_000
        r = audit_record(src, NOW)
        self.assertIsNone(r["pbr_reference_unverified"])
        self.assertIsNotNone(r["per_reference"])
        self.assertIn("PBR_DENOMINATOR_MISSING_OR_ARITHMETIC_MISMATCH", r["quality_flags"])

    def test_missing_pbr_denominator_suppresses_reference(self):
        src = sample()
        src["parent_equity_sgd_thousands"] = None
        r = audit_record(src, NOW)
        self.assertIsNone(r["pbr_reference_unverified"])

    def test_missing_gross_without_pdf_evidence_remains_unverified_not_fabricated(self):
        src = sample()
        for key in ("gross_issued_shares", "treasury_shares", "shares_pdf_sha256"):
            src.pop(key)
        r = audit_record(src, NOW)
        self.assertNotIn("TREASURY_SHARE_ARITHMETIC_OR_BASIS_MISMATCH", r["quality_flags"])
        self.assertFalse(r["ranking_eligible"])


if __name__ == "__main__":
    unittest.main()
