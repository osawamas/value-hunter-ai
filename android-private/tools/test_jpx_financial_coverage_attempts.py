"""Regression tests for acquisition coverage; no live prices or PDFs."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).with_name("jpx_financial_coverage_audit.py")
spec = importlib.util.spec_from_file_location("jpx_coverage_audit", MODULE)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

A = "a" * 64
B = "b" * 64

class CoverageAuditTest(unittest.TestCase):
    def test_unattempted_and_mixed_are_distinct(self):
        universe = {"1234", "5678", "9012"}
        manifest = [
            {"code": "1234", "sha256": A},
            {"code": "1234", "sha256": B},
            {"code": "5678", "sha256": A},
        ]
        report = {"sources": [
            {"code": "1234", "sha256": A, "status": "downloaded"},
            {"code": "1234", "sha256": B, "status": "failed"},
        ]}
        result = audit_module.audit(universe, manifest, report)
        self.assertEqual(result["acquired_codes_in_universe"], 1)
        self.assertEqual(result["mixed_acquisition_codes_in_universe"], 1)
        self.assertEqual(result["unattempted_manifest_codes_in_universe"], ["5678"])
        self.assertEqual(result["missing_manifest_codes"], ["9012"])
        self.assertEqual(result["acquisition_attempted_source_count"], 2)
        self.assertEqual(result["financial_verified_count"], 0)

    def test_duplicate_result_cannot_inflate_attempts(self):
        manifest = [{"code": "1234", "sha256": A}]
        report = {"sources": [
            {"code": "1234", "sha256": A, "status": "downloaded"},
            {"code": "1234", "sha256": A, "status": "failed"},
        ]}
        with self.assertRaisesRegex(ValueError, "Duplicate acquisition"):
            audit_module.audit({"1234"}, manifest, report)

    def test_no_report_is_not_no_missing_originals(self):
        result = audit_module.audit({"1234"}, [{"code": "1234", "sha256": A}])
        self.assertEqual(result["unattempted_manifest_code_count"], 1)
        self.assertEqual(result["acquisition_attempted_source_count"], 0)

if __name__ == "__main__":
    unittest.main()
