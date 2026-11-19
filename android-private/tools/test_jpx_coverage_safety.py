"""Regression tests for private JPX coverage audit (no price or PDF uploads)."""
import unittest

from jpx_financial_coverage_audit import audit

A = "a" * 64
B = "b" * 64
C = "c" * 64


class AuditSafetyTests(unittest.TestCase):
    def test_mixed_and_unattempted_are_not_financially_verified(self):
        universe = {"1234", "5678", "9012"}
        manifest = [
            {"code": "1234", "sha256": A},
            {"code": "1234", "sha256": B},
            {"code": "5678", "sha256": C},
        ]
        report = {"sources": [
            {"code": "1234", "sha256": A, "status": "downloaded"},
            {"code": "1234", "sha256": B, "status": "failed"},
        ]}
        result = audit(universe, manifest, report)
        self.assertEqual(result["manifest_source_records"], 3)
        self.assertEqual(result["acquired_codes_in_universe"], 1)
        self.assertEqual(result["mixed_acquisition_codes"], ["1234"])
        self.assertEqual(result["unattempted_manifest_codes_in_universe"], ["5678"])
        self.assertEqual(result["missing_manifest_codes"], ["9012"])
        self.assertEqual(result["unattempted_manifest_source_count"], 1)
        self.assertEqual(result["financial_verified_count"], 0)
        self.assertEqual(result["notification_eligible_count"], 0)

    def test_report_cannot_claim_unknown_source(self):
        with self.assertRaises(ValueError):
            audit({"1234"}, [{"code": "1234", "sha256": A}],
                  {"sources": [{"code": "1234", "sha256": B, "status": "downloaded"}]})

    def test_duplicate_result_is_rejected(self):
        item = {"code": "1234", "sha256": A, "status": "cached"}
        with self.assertRaises(ValueError):
            audit({"1234"}, [{"code": "1234", "sha256": A}],
                  {"sources": [item, item]})

    def test_invalid_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            audit({"1234"}, [{"code": "1234", "sha256": "invalid"}])

    def test_no_report_does_not_imply_acquisition(self):
        result = audit({"1234"}, [{"code": "1234", "sha256": A}])
        self.assertEqual(result["acquired_codes_in_universe"], 0)
        self.assertEqual(result["unattempted_manifest_source_count"], 1)


if __name__ == "__main__":
    unittest.main()
