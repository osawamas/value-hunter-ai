"""v71: verify exact bank Group cross-foot, PDF identity and scale separation."""
import copy
import unittest
from bank_audited_publish_v71 import crosscheck
from bank_audited_group_v70 import VALUES
from o39_bank_summary_v67 import VALUES as O39_SUMMARY, SOURCE as O39_URL
from u11_bank_summary_v68 import EXPECTED as U11_SUMMARY,SOURCE as U11_URL

def build(symbol):
    spec=VALUES[symbol]
    annual=O39_SUMMARY if symbol=="O39" else U11_SUMMARY
    metrics={}
    for k,(label,nums) in annual.items():
        metrics[k]={"2025": nums[0] if symbol=="O39" else nums[-1],
                    "2024": nums[1] if symbol=="O39" else nums[-2]}
    source=O39_URL if symbol=="O39" else U11_URL
    feed={
        "schema_version":"value_hunter_web_v29",
        "records":[{
            "symbol":symbol,"ranking_eligible":False,
            "price_sgd":None,"market_cap_sgd":None,
            "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None,
            "banking_summary":{
                "status":"ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024",
                "pdf_sha256":"b"*64,
                "source_url":source,"fiscal_year":2025,
                "rounded_balance_unit":"SGD_billions_rounded" if symbol=="U11" else None,
                "values":metrics,
            }
        }]
    }
    inc={k:{"2025":a,"2024":b} for k,(label,(a,b)) in spec["income"].items()}
    bal={k:{"2025":a,"2024":b} for k,(label,(a,b)) in spec["balance"].items()}
    if symbol=="O39":bal["parent_equity"]={"2025":61768,"2024":59316}
    audit={
        "symbol":symbol,
        "status":"BANK_GROUP_AUDITED_2025_2024_ISSUER_PDF_RECONCILED",
        "source_url":source,"pdf_sha256":"b"*64,
        "record":{
            "symbol":symbol,"scope":"AUDITED_ISSUER_GROUP_STATEMENTS_NOT_STANDALONE_BANK",
            "reporting_period_end":"2025-12-31",
            "unit":"SGD_millions","ranking_eligible":False,
            "source_pages":{"income":spec["pages"][0],"balance":spec["pages"][1]},
            "income":inc,"balance":bal,
        }
    }
    return feed,audit

class CrosscheckTests(unittest.TestCase):
    def test_two_issuers_match_in_banking_only_scope(self):
        for sym in ("O39","U11"):
            feed,audit=build(sym)
            result=crosscheck(feed,audit)
            self.assertEqual(result["records"][0]["banking_audited"]["unit"],"SGD_millions")
            self.assertFalse(result["records"][0]["ranking_eligible"])
            self.assertIsNone(result["records"][0]["per_reference"])
            self.assertIsNone(result["records"][0]["pbr_reference_unverified"])
            self.assertNotIn("banking_audited",feed["records"][0])
        self.assertEqual(result["records"][0]["banking_audited"]["balance"]["parent_equity"]["2025"],51248)

    def test_mismatching_pdf_sha_rejected(self):
        feed,audit=build("O39");audit["pdf_sha256"]="a"*64
        with self.assertRaises(ValueError):crosscheck(feed,audit)

    def test_mismatching_income_rejected(self):
        feed,audit=build("U11")
        audit["record"]["income"]["total_income"]["2025"]+=1
        with self.assertRaises(ValueError):crosscheck(feed,audit)

    def test_wrong_audited_balance_rejected(self):
        feed,audit=build("O39")
        audit["record"]["balance"]["total_assets"]["2024"]+=1
        with self.assertRaises(ValueError):crosscheck(feed,audit)

    def test_rounded_summary_crosschecked_with_tolerance(self):
        feed,audit=build("U11")
        feed["records"][0]["banking_summary"]["values"]["total_assets_rounded_billions"]["2025"]=573
        with self.assertRaises(ValueError):crosscheck(feed,audit)

    def test_must_not_promote_valuation(self):
        feed,audit=build("U11")
        feed["records"][0]["price_sgd"]=10.0
        with self.assertRaises(ValueError):crosscheck(feed,audit)

    def test_wrong_reporting_period_rejected(self):
        feed,audit=build("O39")
        audit["record"]["reporting_period_end"]="2024-12-31"
        with self.assertRaises(ValueError):crosscheck(feed,audit)

if __name__=="__main__":
    unittest.main()
