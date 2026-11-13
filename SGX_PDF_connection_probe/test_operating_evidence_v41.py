import unittest
from datetime import datetime, timezone
from value_hunter_v28 import evaluate

NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)

class OperatingProfitEvidenceTests(unittest.TestCase):
    def test_operating_profit_evidence_is_passed_through_without_enabling_ranking(self):
        financial = {"symbol":"S63","fiscal_year":2025,"metrics":{
          "revenue":{"2025":{"value":12346426}},
          "operating_profit":{"2025":{"value":843116}},
          "attributable_profit":{"2025":{"value":462770}},
          "assets":{"2025":{"value":100}},
          "liabilities":{"2025":{"value":30}},
          "equity":{"2025":{"value":70}}
        }}
        audit = {"symbol":"S63","url":"https://example.com/issuer.pdf","checks":[
          {"metric":"revenue","status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"},
          {"metric":"attributable_profit","status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"},
          {"metric":"operating_profit","status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT",
           "reference_extraction":{"evidence":[{"page":2,"row":"Profit from operations"}]}}
        ]}
        out=evaluate(financial,{"symbol":"S63"},audit,NOW)
        self.assertEqual(out["audit_states"]["operating_profit"],"MATCH_LIVE_SECOND_ISSUER_DOCUMENT")
        self.assertEqual(out["audit_pages_by_metric"]["operating_profit"],[2])
        self.assertFalse(out["ranking_eligible"])
        self.assertIn("INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE",out["exclusion_reasons"])

    def test_unverified_operating_profit_is_not_claimed_matched(self):
        out=evaluate({"symbol":"S63","fiscal_year":2025,"metrics":{}},
                     {"symbol":"S63"},{"symbol":"S63","checks":[]},NOW)
        self.assertEqual(out["audit_states"]["operating_profit"],"NOT_VERIFIED")
        self.assertEqual(out["audit_pages_by_metric"]["operating_profit"],[])

if __name__ == "__main__":
    unittest.main()
