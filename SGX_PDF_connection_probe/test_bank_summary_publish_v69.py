"""OCBC/UOB summary-only feed promotion: all valuations must stay null."""
import copy
import unittest
from bank_summary_publish_v69 import add_bank_summary
from o39_bank_summary_v67 import VALUES as OCBC, SOURCE as OCBC_URL
from u11_bank_summary_v68 import EXPECTED as UOB, SOURCE as UOB_URL


def feed():
    return {"schema_version":"value_hunter_web_v29",
            "records":[{"symbol":sym,"financial_source_kind":"REGISTERED_SOURCE_NOT_PARSED",
                        "financial_source_url":url,"ranking_eligible":False,
                        "price_sgd":None,"market_cap_sgd":None,"per_reference":None,
                        "pbr_reference_unverified":None}
                       for sym,url in [("O39",OCBC_URL),("U11",UOB_URL)]]}


def evidence(sym):
    if sym=="O39":
        return {"symbol":sym,
                "status":"O39_ISSUER_2025_GROUP_FINANCIAL_HIGHLIGHTS_MATCHED",
                "source_url":OCBC_URL,"pdf_sha256":"c"*64,
                "record":{"scope":"ISSUER_SELECTED_GROUP_FINANCIAL_HIGHLIGHTS",
                          "fiscal_year":2025,"unit":"SGD_millions",
                          "ranking_eligible":False,
                          "metrics":{k:{"2025":a[1][0],"2024":a[1][1]}
                                     for k,a in OCBC.items()}}}
    return {"symbol":sym,
            "status":"U11_FY2025_ISSUER_FIVE_YEAR_BANK_SUMMARY_MATCHED",
            "source_url":UOB_URL,"pdf_sha256":"a"*64,
            "record":{"scope":"ISSUER_FIVE_YEAR_GROUP_SUMMARY_NOT_DIRECT_AUDITED_STATEMENTS",
                      "fiscal_year":2025,"financials_unit":"SGD_millions",
                      "rounded_balance_unit":"SGD_billions_rounded",
                      "ranking_eligible":False,
                      "metrics":{k:{"2025":a[1][-1],"2024":a[1][-2]}
                                 for k,a in UOB.items()}}}


class SummaryPublishingTests(unittest.TestCase):
    def test_both_sources_separate_and_no_valution(self):
        result=feed()
        for sym in ("O39","U11"):
            result=add_bank_summary(result,evidence(sym))
        for r in result["records"]:
            self.assertIsNone(r["per_reference"])
            self.assertIsNone(r["pbr_reference_unverified"])
            self.assertIsNone(r["price_sgd"])
            self.assertFalse(r["ranking_eligible"])
            self.assertEqual(r["banking_summary"]["fiscal_year"],2025)
        self.assertEqual(result["records"][1]["banking_summary"]["rounded_balance_unit"],"SGD_billions_rounded")
        self.assertIsNone(result["records"][0]["banking_summary"]["rounded_balance_unit"])

    def test_missing_data_rejected(self):
        e=evidence("O39")
        e["record"]["metrics"].pop("total_income")
        with self.assertRaises(ValueError):add_bank_summary(feed(),e)

    def test_mismatched_source_rejected(self):
        e=evidence("U11");e["source_url"]="https://other.example.org/a.pdf"
        with self.assertRaises(ValueError):add_bank_summary(feed(),e)

    def test_unverified_pdf_rejected(self):
        e=evidence("O39");e["status"]="NOT_VERIFIED"
        with self.assertRaises(ValueError):add_bank_summary(feed(),e)

    def test_rounded_bank_assets_cannot_claim_precision(self):
        e=evidence("U11");e["record"]["rounded_balance_unit"]="SGD_millions"
        with self.assertRaises(ValueError):add_bank_summary(feed(),e)

    def test_reject_synthetic_quote(self):
        data=feed();data["records"][0]["price_sgd"]=4.4
        with self.assertRaises(ValueError):add_bank_summary(data,evidence("O39"))

if __name__=="__main__":unittest.main()
