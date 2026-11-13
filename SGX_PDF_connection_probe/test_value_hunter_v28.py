import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from value_hunter_v28 import compare, write, age_quote

NOW = datetime(2026, 11, 13, 5, 0, tzinfo=timezone.utc)


def sample():
    fin = {"records": [
        {"symbol": "S68", "fiscal_year": 2026, "source_kind": "HISTORICAL_V14_ISSUER_SPECIFIC_FIXTURE", "metrics": {}},
        {"symbol": "G13", "fiscal_year": 2025, "source_kind": "LIVE_V18_PDF_EXTRACT", "metrics": {
            "revenue": {"2025": {"value": 2452053}, "2024": {"value": 2529960}},
            "attributable_profit": {"2025": {"value": 390346}},
            "assets": {"2025": {"value": 9000}},
            "liabilities": {"2025": {"value": 4000}},
            "equity": {"2025": {"value": 5000}},
            "operating_profit": {"2025": {"value": 506609}}
        }},
        {"symbol": "S20", "fiscal_year": 2025, "metrics": {
            "attributable_profit": {"2025": {"value": -249133}}}},
    ]}
    valuation = {"records": [
        {"symbol": "G13", "quote": {"price_sgd": 0.57, "market_timestamp_utc": "2026-11-13T03:00:00+00:00",
                                  "source_url": "https://example.com/quote"},
         "shares": {"shares_outstanding": 12000000000, "as_of_date": "2026-08-17",
                    "share_count_basis": "issued_excluding_treasury", "source_url": "https://example.com/shares"},
         "parent_equity_sgd_thousands": 8200000, "parent_equity_status": "REFERENCE_UNVERIFIED"},
    ]}
    audit = {"records": [
        {"symbol": "G13", "checks": [
            {"metric": "revenue", "status": "MATCH_LIVE_SECOND_ISSUER_DOCUMENT"},
            {"metric": "attributable_profit", "status": "MATCH_LIVE_SECOND_ISSUER_DOCUMENT"}]},
    ]}
    return fin, valuation, audit


class V28Tests(unittest.TestCase):
    def test_three_symbols_and_no_false_ranking(self):
        result = compare(*sample(), NOW)
        self.assertEqual([x["symbol"] for x in result["records"]], ["S68", "G13", "S20"])
        self.assertEqual(result["ranking_eligible_count"], 0)

    def test_g13_calculation_and_exclusion(self):
        g13 = compare(*sample(), NOW)["records"][1]
        self.assertEqual(g13["market_cap_sgd"], 6840000000)
        self.assertAlmostEqual(g13["per_reference"], 17.5229, places=3)
        self.assertEqual(g13["revenue_growth_pct"], -3.08)
        self.assertIsNone(g13["pbr_verified"])
        self.assertIn("INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE", g13["exclusion_reasons"])

    def test_s68_fixed_is_blocked(self):
        s68 = compare(*sample(), NOW)["records"][0]
        self.assertIn("HISTORICAL_FIXED_FINANCIALS", s68["exclusion_reasons"])

    def test_negative_profit_has_no_per(self):
        s20 = compare(*sample(), NOW)["records"][2]
        self.assertIsNone(s20["per_reference"])
        self.assertIn("NEGATIVE_EARNINGS_PER_NOT_APPLICABLE", s20["exclusion_reasons"])

    def test_missing_price_does_not_invent_market_cap(self):
        g13 = compare(*sample(), NOW)["records"][1]
        g13 # existence
        fin, val, audit = sample()
        val["records"][0]["quote"]["price_sgd"] = None
        result = compare(fin, val, audit, NOW)["records"][1]
        self.assertIsNone(result["market_cap_sgd"])
        self.assertIn("PRICE_MISSING", result["exclusion_reasons"])

    def test_stale_price(self):
        fin, val, audit = sample()
        val["records"][0]["quote"]["market_timestamp_utc"] = "2025-01-01T00:00:00Z"
        result = compare(fin, val, audit, NOW)["records"][1]
        self.assertIn("QUOTE_OLD_OR_UNDATED", result["exclusion_reasons"])

    def test_report_files(self):
        with tempfile.TemporaryDirectory() as out:
            write(compare(*sample(), NOW), out)
            self.assertTrue(Path(out, "comparison_v28.json").exists())
            self.assertIn("G13", Path(out, "summary_v28.md").read_text())

    def test_invalid_timestamp(self):
        self.assertIsNone(age_quote("broken", NOW))
        self.assertIsNone(age_quote(None, NOW))


if __name__ == "__main__":
    unittest.main()
