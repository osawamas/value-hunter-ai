"""Regression tests for private batch screening; no network or market prices."""
import unittest
from jpx_batch_financial_screen import screen


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
