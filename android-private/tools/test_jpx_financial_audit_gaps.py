"""Actionable issuer-level acquisition audit regression tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jpx_financial_coverage_audit import audit

A = "a" * 64
B = "b" * 64
C = "c" * 64

class AuditGapTests(unittest.TestCase):
    def test_mixed_failed_only_and_unattempted_are_separate(self):
        universe = {"1234", "5678", "9012", "3456"}
        manifest = [
            {"code": "1234", "sha256": A},
            {"code": "1234", "sha256": B},
            {"code": "5678", "sha256": C},
            {"code": "9012", "sha256": A},
        ]
        report = {"sources": [
            {"code": "1234", "sha256": A, "status": "downloaded"},
            {"code": "1234", "sha256": B, "status": "failed"},
            {"code": "5678", "sha256": C, "status": "failed"},
        ]}
        result = audit(universe, manifest, report)
        self.assertEqual(result["failed_only_codes"], ["5678"])
        self.assertEqual(result["mixed_acquisition_codes"], ["1234"])
        self.assertEqual(result["acquired_only_codes"], [])
        self.assertEqual(result["unattempted_manifest_codes_in_universe"], ["9012"])
        self.assertEqual(result["missing_manifest_codes"], ["3456"])
        self.assertEqual(result["unattempted_manifest_source_count"], 1)
        self.assertEqual(result["financial_verified_count"], 0)
        self.assertEqual(result["notification_eligible_count"], 0)

    def test_duplicate_original_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate source identity"):
            audit({"1234"}, [{"code": "1234", "sha256": A},
                             {"code": "1234", "sha256": A}])

if __name__ == "__main__":
    unittest.main()
