"""Regression tests for market-specific audit accounting."""
import copy
import json
import unittest
from pathlib import Path
from scripts.validate_us_market_audit import validate


class UsAuditInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(Path("docs/us-market-audit-20261117.json").read_text(encoding="utf-8"))

    def test_saved_evidence_is_consistent(self):
        self.assertEqual([], validate(self.audit))

    def test_rejects_market_total_mismatch(self):
        value = copy.deepcopy(self.audit)
        value["listing_market_counts"]["NYSE"]["covered"] -= 1
        self.assertIn("market totals disagree", validate(value))

    def test_rejects_missing_hold_symbol(self):
        value = copy.deepcopy(self.audit)
        value["nasdaq_hold_reason_by_ticker"].pop(next(iter(value["nasdaq_hold_reason_by_ticker"])))
        self.assertIn("Nasdaq hold count differs from uncovered", validate(value))

    def test_rejects_cross_category_symbol(self):
        value = copy.deepcopy(self.audit)
        value["nasdaq_verified_pair"].append(next(iter(value["nasdaq_hold_reason_by_ticker"])))
        self.assertIn("Nasdaq symbol both verified and held", validate(value))

    def test_rejects_missing_nyse_evidence(self):
        value = copy.deepcopy(self.audit)
        value["nyse_nasdaq_public_history_status_by_ticker"].pop(next(iter(value["nyse_nasdaq_public_history_status_by_ticker"])))
        self.assertIn("NYSE evidence missing or extraneous", validate(value))


if __name__ == "__main__":
    unittest.main()
