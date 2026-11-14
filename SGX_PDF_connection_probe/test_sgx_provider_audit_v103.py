"""Regression tests for v103 provider-only audit."""
import json
import unittest
from sgx_provider_audit_v103 import inspect

def raw(items):
    return json.dumps({"data": items, "meta": {"total": len(items)}}).encode()

def rows():
    return [{"ticker": f"A{i:02d}", "company_name": f"Company {i:02d}"} for i in range(25)]

class AuditTests(unittest.TestCase):
    def test_bad_ticker_and_status_flags_are_never_official(self):
        data = rows()
        data[0]["is_active"] = False
        data[1]["delisting_date"] = "2026-01-02"
        data.append({"ticker": "BAD-TICKER", "company_name": "Unusable Co"})
        result = inspect(raw(data))
        self.assertEqual(result["rejected_rows"], 1)
        self.assertEqual(result["accepted_rows"], 25)
        self.assertEqual(result["rejected_row_details"][0]["reason_codes"], ["INVALID_OR_MISSING_TICKER"])
        self.assertEqual(result["status_field_counts"]["explicit_inactive"], 2)
        self.assertFalse(result["sgx_master_comparison_completed"])
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["promoted_to_financial_feed"])
        self.assertTrue(all(not r["sgx_official_listing_status_verified"] for r in result["provider_status_signals"]))
    def test_missing_status_is_unknown_not_active(self):
        result = inspect(raw(rows()))
        self.assertEqual(result["status_field_counts"]["active_unknown"], 25)
        self.assertEqual(result["status_field_counts"]["active_true"], 0)
    def test_duplicate_does_not_raise_official_count(self):
        data = rows()
        data.append(dict(data[0]))
        result = inspect(raw(data))
        self.assertEqual(result["accepted_rows"], 25)
        self.assertEqual(result["rejected_rows"], 1)

if __name__ == "__main__":
    unittest.main()
