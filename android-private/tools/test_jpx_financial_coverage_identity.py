"""Ensure a downloaded PDF is never credited to another issuer original."""
import unittest
from jpx_financial_coverage_audit import audit


class ExactOriginalAuditTests(unittest.TestCase):
    def setUp(self):
        self.universe = {"1234", "5678"}
        self.manifest = [
            {"code": "1234", "url": "https://issuer.example/a.pdf", "sha256": "a" * 64},
            {"code": "5678", "url": "https://issuer.example/b.pdf", "sha256": "b" * 64},
        ]

    def test_matching_original_counts_as_acquired_not_verified(self):
        report = {"sources": [{"code": "1234", "sha256": "a" * 64,
                               "status": "downloaded"}]}
        result = audit(self.universe, self.manifest, report)
        self.assertEqual(result["acquired_codes_in_universe"], 1)
        self.assertEqual(result["financial_verified_count"], 0)
        self.assertEqual(result["notification_eligible_count"], 0)

    def test_same_issuer_wrong_original_is_rejected(self):
        report = {"sources": [{"code": "1234", "sha256": "c" * 64,
                               "status": "downloaded"}]}
        with self.assertRaisesRegex(ValueError, "source not in manifest"):
            audit(self.universe, self.manifest, report)

    def test_other_issuer_original_is_rejected(self):
        report = {"sources": [{"code": "1234", "sha256": "b" * 64,
                               "status": "cached"}]}
        with self.assertRaises(ValueError):
            audit(self.universe, self.manifest, report)

    def test_manifest_without_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256"):
            audit(self.universe, [{"code": "1234", "url": "https://issuer.example/a.pdf"}])


if __name__ == "__main__":
    unittest.main()
