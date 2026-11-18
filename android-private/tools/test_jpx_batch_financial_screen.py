"""Regression tests for private batch screening; no network or market prices."""
from datetime import date
from decimal import Decimal
import unittest

from jpx_batch_financial_screen import screen, screen_report


class BatchScreenTests(unittest.TestCase):
    def test_two_updates_and_guardrails(self):
        base = {"trade_date": "2026-11-16", "observations": [
            {"code": "1301", "close": "800", "financial_as_of": "2026-09-30",
             "financial_verified": True, "share_basis_verified": True,
             "per": "12", "pbr": "0.8"},
            {"code": "3861", "close": "700", "financial_as_of": "2026-09-30",
             "financial_verified": False, "share_basis_verified": True,
             "per": "8", "pbr": "0.5"}]}
        first = screen(base)
        self.assertEqual(first["tiers"]["priority"], 1)
        self.assertEqual(first["tiers"]["held"], 1)
        second = screen(base)
        self.assertEqual(first, second)
        self.assertNotIn("observations", first)
        self.assertNotIn("close", str(first))

    def test_verified_flags_without_financial_date_are_held(self):
        payload = {"trade_date": "2026-11-16", "observations": [
            {"code": "1301", "close": "800", "financial_verified": True,
             "share_basis_verified": True, "per": "12", "pbr": "0.8"}]}
        result = screen(payload)
        self.assertEqual(result["tiers"]["priority"], 0)
        self.assertEqual(result["tiers"]["held"], 1)
        self.assertEqual(result["reasons"]["fundamentals_unavailable"], 1)

    def test_report_supports_letter_codes_and_uses_filing_and_rights_dates(self):
        day = date(2026, 9, 30)
        period = date(2026, 8, 31)
        published = date(2026, 9, 15)
        stocks = {"130A": "growth", "3861": "prime", "7203": "prime", "9432": "prime"}
        prices = {code: (None, Decimal("900")) for code in stocks}
        filings = [
            ("130A", period, published, {"eps_jpy": "60", "bps_jpy": "900"}),
            ("3861", period, published, {"eps_jpy": "-60", "bps_jpy": "900"}),
            ("7203", period, day, {"eps_jpy": "60", "bps_jpy": "900"}),
        ]
        rights = ({date(2026, 8, 1), date(2026, 9, 1)}, {})
        report = screen_report(day, stocks, prices, {"9432"}, filings, rights)
        self.assertEqual(report["tiers"]["priority"], 1)
        self.assertEqual(report["source_counts"]["financial_basis_verified"], 2)
        self.assertEqual(report["source_counts"]["both_ratios_usable"], 1)
        self.assertEqual(report["source_counts"]["incomplete_or_nonpositive_ratios"], 1)
        self.assertEqual(report["reasons"]["nonpositive_or_invalid_fundamentals"], 1)
        self.assertEqual(report["source_counts"]["financials_not_yet_public"], 1)
        self.assertEqual(report["source_counts"]["ambiguous_close"], 1)

        gap = screen_report(day, stocks, prices, {"9432"}, filings, (set(), {}))
        self.assertEqual(gap["tiers"]["priority"], 0)
        self.assertEqual(gap["source_counts"]["hold_rights_report_gap"], 2)

    def test_future_financial_date_rejected(self):
        with self.assertRaises(ValueError):
            screen({"trade_date": "2026-11-16", "observations": [
                {"code": "1301", "close": "500", "financial_as_of": "2026-11-17"}]})

    def test_duplicate_code_rejected(self):
        with self.assertRaises(ValueError):
            screen({"trade_date": "2026-11-16", "observations": [
                {"code": "1301", "close": "500"}, {"code": "1301", "close": "500"}]})


if __name__ == "__main__":
    unittest.main()
