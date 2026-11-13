"""v59: S68 annual-report audit and shareholding extraction must cite same PDF."""
import json
import tempfile
import unittest
from pathlib import Path
from value_hunter_v27 import validate_s68_crosscheck


class AnnualIdentityTests(unittest.TestCase):
    def setUp(self):
        self.finance={"S68":{"symbol":"S68","pdf_sha256":"e"*64,
           "source_url":"https://example.org/results.pdf",
           "metrics":{"revenue":{"2026":{"value":1559469}},
                      "attributable_profit":{"2026":{"value":698411}}}}}
        self.audit={"symbol":"S68","status":"SECOND_ISSUER_ANNUAL_REPORT_MATCHED",
            "source_url":"https://example.org/annual.pdf","pdf_sha256":"a"*64,
            "checks":[{"metric":m,"year":2026,"reference_value":value,
                       "status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"}
                      for m,value in [("revenue",1559469),("attributable_profit",698411)]]}
        self.shares={"symbol":"S68",
            "status":"OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED",
            "source_url":self.audit["source_url"],"pdf_sha256":self.audit["pdf_sha256"],
            "snapshot":{"as_of_date":"2026-09-01","shares_outstanding":1070843484}}
    def check(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp); ap=parent/"audit.json";sp=parent/"shares.json"
            ap.write_text(json.dumps(self.audit),encoding="utf-8")
            sp.write_text(json.dumps(self.shares),encoding="utf-8")
            return validate_s68_crosscheck(self.finance,ap,sp)

    def test_equal_issuer_document_hash_and_url(self):
        result=self.check()
        self.assertEqual(result["status"],"S68_ANNUAL_ISSUER_CROSSCHECK_MATCHED")
        self.assertFalse(result["investment_ranking_eligible"])

    def test_wrong_sha_rejected(self):
        self.shares["pdf_sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"SHA/date mismatch"):self.check()

    def test_wrong_url_rejected(self):
        self.shares["source_url"]="https://example.org/different.pdf"
        with self.assertRaises(ValueError):self.check()

    def test_wrong_date_rejected(self):
        self.shares["snapshot"]["as_of_date"]="2025-09-01"
        with self.assertRaises(ValueError):self.check()

    def test_unverified_share_extraction_rejected(self):
        self.shares["status"]="NOT_VERIFIED"
        with self.assertRaises(ValueError):self.check()


if __name__=="__main__":unittest.main()
