import unittest
from scripts.audit_jpx_financial_evidence import audit

HASH = "a" * 64


class EvidenceAuditTests(unittest.TestCase):
    def test_hold_reason_ticker_mapping_is_sorted_and_accounted(self):
        result = audit({"universe": ["1234", "5678", "9012"], "records": [
            {"ticker": "5678", "on_hold": True, "hold_reason": "split review"},
            {"ticker": "1234", "on_hold": True, "hold_reason": "split review"},
            {"ticker": "9012", "on_hold": True}
        ]})
        self.assertEqual(result["codes_by_hold_reason"], {"split review": ["1234", "5678"]})
        self.assertEqual(result["hold_reasons"], {"split review": 2})
        self.assertEqual(result["hold_reason_unclassified"], 1)
        self.assertEqual(result["on_hold"], 3)

    def test_reason_without_hold_or_with_eligible_rejected(self):
        for record in (
            {"ticker": "1234", "hold_reason": "split review"},
            {"ticker": "1234", "financial_eligible": True, "hold_reason": "split review"},
            {"ticker": "1234", "on_hold": True, "hold_reason": " "}
        ):
            with self.assertRaises(ValueError):
                audit({"universe": ["1234"], "records": [record]})

    def test_mixed_evidence_hold_reasons_reconcile_without_inventing_codes(self):
        result = audit({"universe": ["1234", "5678", "9012", "3456"], "records": [
            {"ticker": "1234", "on_hold": True, "hold_reason": "split review",
             "source_url": "https://www2.jpx.co.jp/disc/12340/123_tse-ace-original-ixbrl.htm",
             "source_sha256": HASH},
            {"ticker": "5678", "on_hold": True, "hold_reason": "missing correction"},
            {"ticker": "9012", "on_hold": True}
        ]})
        self.assertEqual(result["source_retrieved"], 1)
        self.assertEqual(result["on_hold"], 3)
        self.assertEqual(result["not_started"], 1)
        self.assertEqual(sum(result["hold_reasons"].values()) +
                         result["hold_reason_unclassified"], result["on_hold"])
        self.assertEqual(result["codes_by_hold_reason"],
                         {"missing correction": ["5678"], "split review": ["1234"]})
        self.assertNotIn("9012", sum(result["codes_by_hold_reason"].values(), []))

    def test_explicit_non_hold_cannot_be_counted_as_held(self):
        address = "https://www2.jpx.co.jp/disc/12340/123_tse-ace-original-ixbrl.htm"
        with self.assertRaises(ValueError):
            audit({"universe": ["1234"], "records": [
                {"ticker": "1234", "source_url": address,
                 "source_sha256": HASH, "financial_eligible": False,
                 "on_hold": False}
            ]})
        # Legacy manifests without an explicit hold flag remain conservatively held.
        result = audit({"universe": ["1234"], "records": [
            {"ticker": "1234", "source_url": address,
             "source_sha256": HASH, "financial_eligible": False}
        ]})
        self.assertEqual(result["on_hold"], 1)
        self.assertEqual(result["hold_reason_unclassified"], 1)

    def test_non_boolean_status_flags_fail_closed(self):
        # JSON manifests may contain "false", 0, or null after bad conversion.
        # None of these should silently turn a held or eligible record into another status.
        for field in ("on_hold", "financial_eligible"):
            for bad_value in ("true", "false", 0, 1, None, [], {}):
                with self.subTest(field=field, value=bad_value):
                    record = {"ticker": "1234", field: bad_value}
                    with self.assertRaises(ValueError):
                        audit({"universe": ["1234"], "records": [record]})
        # Explicit booleans and omitted legacy flags still work.
        self.assertEqual(audit({"universe": ["1234"], "records": [
            {"ticker": "1234", "on_hold": True}
        ]})["on_hold"], 1)
        self.assertEqual(audit({"universe": ["1234"], "records": [
            {"ticker": "1234"}
        ]})["not_started"], 1)

    def test_supplied_partial_or_mismatched_evidence_fails_closed(self):
        valid = "https://www2.jpx.co.jp/disc/12340/123_tse-ace-original-ixbrl.htm"
        wrong_ticker = "https://www2.jpx.co.jp/disc/56780/123_tse-ace-original-ixbrl.htm"
        for supplied in (
            {"source_url": valid},
            {"source_sha256": HASH},
            {"source_url": valid, "source_sha256": "bad"},
            {"source_url": wrong_ticker, "source_sha256": HASH},
            {"source_url": None, "source_sha256": HASH},
        ):
            for held in (False, True):
                with self.subTest(supplied=supplied, held=held):
                    record = {"ticker": "1234", "on_hold": held, **supplied}
                    with self.assertRaises(ValueError):
                        audit({"universe": ["1234"], "records": [record]})
        # Truly absent evidence remains a valid, explicitly held record.
        self.assertEqual(audit({"universe": ["1234"], "records": [
            {"ticker": "1234", "on_hold": True}
        ]})["on_hold"], 1)

    def test_missing_original_never_counts_as_retrieved(self):
        result = audit({"universe": ["1234", "5678"], "records": [
            {"ticker": "1234", "financial_eligible": False, "on_hold": True}
        ]})
        self.assertEqual(result["source_retrieved"], 0)
        self.assertEqual(result["on_hold"], 1)
        self.assertEqual(result["not_started"], 1)

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
