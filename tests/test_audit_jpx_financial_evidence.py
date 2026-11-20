import unittest
from scripts.audit_jpx_financial_evidence import audit

HASH = "a" * 64


class EvidenceAuditTests(unittest.TestCase):
    def test_missing_original_never_counts_as_retrieved(self):
        result = audit({"universe": ["1234", "5678"], "records": [
            {"ticker": "1234", "financial_eligible": False, "on_hold": True}
        ]})
        self.assertEqual(result["source_retrieved"], 0)
        self.assertEqual(result["on_hold"], 1)
        self.assertEqual(result["not_started"], 1)

    def test_verified_original_and_hold(self):
        result = audit({"universe": ["1234", "5678"], "records": [
            {"ticker": "1234", "source_url": "https://example.org/original.pdf",
             "source_sha256": HASH, "financial_eligible": True},
            {"ticker": "5678", "source_url": "https://example.org/correction.pdf",
             "source_sha256": HASH, "on_hold": True}
        ]})
        self.assertEqual(result["source_retrieved"], 2)
        self.assertEqual(result["financial_eligible"], 1)
        self.assertEqual(result["on_hold"], 1)

    def test_eligible_without_evidence_rejected(self):
        with self.assertRaises(ValueError):
            audit({"universe": ["1234"], "records": [
                {"ticker": "1234", "financial_eligible": True}
            ]})

    def test_duplicate_record_rejected(self):
        with self.assertRaises(ValueError):
            audit({"universe": ["1234"], "records": [
                {"ticker": "1234"}, {"ticker": "1234"}
            ]})


if __name__ == "__main__":
    unittest.main()
