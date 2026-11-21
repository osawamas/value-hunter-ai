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

    def test_attempted_without_original_is_held_not_unstarted(self):
        result = audit({"universe": ["1234", "5678", "9012"], "records": [
            {"ticker": "1234", "reason": "rate_limited_before_request"},
            {"ticker": "5678", "reason": "source_unavailable", "on_hold": True}
        ]})
        self.assertEqual(result["source_retrieved"], 0)
        self.assertEqual(result["financial_eligible"], 0)
        self.assertEqual(result["on_hold"], 2)
        self.assertEqual(result["not_started"], 1)
        self.assertEqual(result["records_seen"], 2)

    def test_verified_original_and_hold(self):
        result = audit({"universe": ["1234", "5678"], "records": [
            {"ticker": "1234", "source_url": "https://www2.jpx.co.jp/disc/12340/123_tse-ace-original-ixbrl.htm",
             "source_sha256": HASH, "financial_eligible": True},
            {"ticker": "5678", "source_url": "https://www2.jpx.co.jp/disc/56780/456_tse-ace-correction-ixbrl.htm",
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

    def test_cross_ticker_or_unofficial_url_never_proves_eligibility(self):
        for address in ("https://example.org/original.pdf",
                        "https://www2.jpx.co.jp/disc/56780/456_tse-ace-correction-ixbrl.htm"):
            with self.assertRaises(ValueError):
                audit({"universe": ["1234"], "records": [
                    {"ticker": "1234", "source_url": address, "source_sha256": HASH, "financial_eligible": True}
                ]})


if __name__ == "__main__":
    unittest.main()
