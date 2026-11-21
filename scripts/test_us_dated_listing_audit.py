"""Regression guard for the public, price-free US dated-listing audit.

Run: python -m unittest discover -s scripts -p 'test_us_dated_listing_audit.py'
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "us-dated-listing-audit-20261117.json"
MARKET = ROOT / "docs" / "us-market-audit-20261117.json"


class DatedListingAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        cls.market = json.loads(MARKET.read_text(encoding="utf-8"))

    def test_market_counts_reconcile(self):
        market = self.market
        counts = market["listing_market_counts"]
        self.assertEqual(sum(v["listed"] for v in counts.values()), market["listed"])
        self.assertEqual(sum(v["covered"] for v in counts.values()), market["covered"])
        self.assertGreaterEqual(market["listed"], market["covered"])

    def test_reference_rows_reconcile_and_are_unique(self):
        audit = self.audit
        rows = audit["rows"]
        summary = audit["summary"]
        keys = [(r["exchange"], r["symbol"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(rows), summary["symbols_reviewed"])
        self.assertEqual(sum(r["provider_close_on_trading_date"] is True for r in rows),
                         summary["same_session_provider_closes"])
        self.assertEqual(sum(r["exact_listing_pair_verified"] is True for r in rows),
                         summary["exact_dated_listing_pairs_verified"])
        self.assertEqual(sum(r["disposition"] == "held" for r in rows), summary["held"])
        self.assertEqual(sum(r["disposition"] == "excluded" for r in rows), summary["excluded"])
        self.assertEqual(summary["held"] + summary["excluded"], len(rows))

    def test_no_unverified_pair_is_admitted(self):
        audit = self.audit
        rows = audit["rows"]
        for row in rows:
            if not row["exact_listing_pair_verified"]:
                self.assertNotEqual(row["disposition"], "admitted", row["symbol"])
        if not any(row["exact_listing_pair_verified"] for row in rows):
            summary = audit["summary"]
            self.assertEqual(summary["newly_admitted_prices"], 0)
            self.assertEqual(summary["additional_financial_screens"], 0)
            self.assertEqual(summary["additional_alert_candidates"], 0)

    def test_audit_dates_and_venues(self):
        audit = self.audit
        self.assertEqual(audit["trading_date_et"], self.market["trading_date"])
        self.assertEqual(audit["comparison_date_et"], self.market["previous_trading_date"])
        for row in audit["rows"]:
            self.assertIn(row["exchange"], ("NYSE", "Nasdaq"))


if __name__ == "__main__":
    unittest.main()
