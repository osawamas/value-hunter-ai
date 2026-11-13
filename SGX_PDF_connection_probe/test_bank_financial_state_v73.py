"""v73 publication status: Group bank audited financials vs generic schema."""
import copy
import unittest
from bank_financial_state_v73 import annotate

def fixture():
    rows=[]
    for sym in ("D05","O39","U11"):
        source={"status":"BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED" if sym=="D05"
                else "ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS",
                "source_url":f"https://example.org/{sym}.pdf",
                "pdf_sha256":"a"*64}
        row={"symbol":sym,"ranking_eligible":False,
             "financial_source_kind":"REGISTERED_SOURCE_NOT_PARSED",
             "financial_source_url":source["source_url"],
             "price_sgd":None,"market_cap_sgd":None,"per_reference":None,
             "pbr_reference_unverified":None,"pbr_verified":None,
             "exclusion_reasons":["FINANCIAL_MISSING_REVENUE",
                 "FINANCIAL_SOURCE_REGISTERED_NOT_PARSED","PRICE_MISSING"]}
        row["banking_evidence" if sym=="D05" else "banking_audited"]=source
        rows.append(row)
    rows.append({"symbol":"S68","ranking_eligible":False,"price_sgd":1.2})
    return {"schema_version":"value_hunter_web_v29","records":rows}

class StatusTests(unittest.TestCase):
    def test_marks_only_verified_bank_data(self):
        original=fixture()
        result=annotate(original)
        for row in result["records"][:3]:
            status=row["bank_financial_state"]
            self.assertTrue(status["banking_metrics_parsed"])
            self.assertTrue(status["generic_industrial_metrics_not_applicable"])
            self.assertFalse(status["third_party_numerical_verification"])
            self.assertFalse(status["ranking_eligible"])
            self.assertIsNone(row["per_reference"])
            self.assertIn("FINANCIAL_MISSING_REVENUE",row["exclusion_reasons"])
        self.assertNotIn("bank_financial_state",result["records"][3])
        self.assertNotIn("bank_financial_state",original["records"][0])

    def test_missing_evidence_not_labeled(self):
        data=fixture()
        data["records"][0].pop("banking_evidence")
        out=annotate(data)
        self.assertNotIn("bank_financial_state",out["records"][0])

    def test_url_mismatch_rejected(self):
        data=fixture()
        data["records"][1]["banking_audited"]["source_url"]="https://example.org/different.pdf"
        with self.assertRaises(ValueError):annotate(data)

    def test_invalid_sha_rejected(self):
        data=fixture()
        data["records"][2]["banking_audited"]["pdf_sha256"]="bad"
        with self.assertRaises(ValueError):annotate(data)

    def test_generic_valuation_not_promoted(self):
        data=fixture()
        data["records"][1]["price_sgd"]=10
        with self.assertRaises(ValueError):annotate(data)

    def test_unknown_status_rejected(self):
        data=fixture()
        data["records"][0]["banking_evidence"]["status"]="NOT_VERIFIED"
        with self.assertRaises(ValueError):annotate(data)

if __name__=="__main__":unittest.main()
