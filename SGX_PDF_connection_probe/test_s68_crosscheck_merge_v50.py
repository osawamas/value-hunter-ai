import json
import tempfile
import unittest
from pathlib import Path
from value_hunter_v27 import validate_s68_crosscheck

class S68IssuerCheckTests(unittest.TestCase):
    def setUp(self):
        self.fin={"S68":{"symbol":"S68","source_url":"https://issuer.test/results.pdf",
            "pdf_sha256":"results-hash",
            "metrics":{"revenue":{"2026":{"value":1559469}},
                       "attributable_profit":{"2026":{"value":698411}}}}}
        self.record={"symbol":"S68","status":"SECOND_ISSUER_ANNUAL_REPORT_MATCHED",
            "source_url":"https://issuer.test/annual.pdf","pdf_sha256":"annual-hash",
            "checks":[{"metric":"revenue","year":2026,"reference_value":1559469,
                    "status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"},
                   {"metric":"attributable_profit","year":2026,
                    "reference_value":698411,"status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"}]}
    def check(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"source.json"
            path.write_text(json.dumps(self.record))
            return validate_s68_crosscheck(self.fin,path)
    def test_distinct_issuer_source_not_third_party(self):
        audit=self.check()
        self.assertEqual(len(audit["checks"]),2)
        self.assertFalse(audit["investment_ranking_eligible"])
        self.assertEqual(audit["reference_type"],"SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY")
    def test_mismatch_rejected(self):
        self.record["checks"][0]["reference_value"]=1
        with self.assertRaises(ValueError):self.check()
    def test_same_source_rejected(self):
        self.record["source_url"]=self.fin["S68"]["source_url"]
        with self.assertRaises(ValueError):self.check()
    def test_incomplete_metric_rejected(self):
        self.record["checks"].pop()
        with self.assertRaises(ValueError):self.check()

if __name__=="__main__":unittest.main()
