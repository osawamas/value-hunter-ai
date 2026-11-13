"""Historical bank indicator math must not create current valuations."""
import copy
import unittest
from bank_indicators_v72 import compute_bank_indicators
from bank_audited_publish_v71 import crosscheck
from test_bank_audited_publish_v71 import build

def sample():
    feed={"schema_version":"value_hunter_web_v29","records":[]}
    d05={
        "symbol":"D05","ranking_eligible":False,
        "price_sgd":None,"market_cap_sgd":None,"per_reference":None,
        "pbr_reference_unverified":None,"pbr_verified":None,
        "banking_evidence":{
            "status":"BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED",
            "unit":"SGD_millions","pdf_sha256":"d"*64,
            "source_url":"https://example.com/dbs.pdf",
            "income":{
                "2025":{"profit_attributable_to_parent":10933,"total_income":22900,"total_expenses":9349},
                "2024":{"profit_attributable_to_parent":11289,"total_income":22297,"total_expenses":9018}},
            "balance":{
                "2025":{"parent_shareholders_funds":68867},
                "2024":{"parent_shareholders_funds":68786}}
        }}
    feed["records"].append(d05)
    for sym in ("O39","U11"):
        pre,proof=build(sym)
        verified=crosscheck(pre,proof)
        feed["records"].append(verified["records"][0])
    return feed


class HistoricalIndicatorTests(unittest.TestCase):
    def test_three_banks_source_backed_proxies(self):
        feed=sample()
        out=compute_bank_indicators(feed)
        found={r["symbol"]:r for r in out["records"]}
        self.assertEqual(set(found),{"D05","O39","U11"})
        self.assertEqual(found["D05"]["banking_indicators"]["values"]["simple_roe_percent"],15.88)
        self.assertEqual(found["O39"]["banking_indicators"]["values"]["cost_to_income_proxy_percent"],40.25)
        self.assertEqual(found["U11"]["banking_indicators"]["values"]["simple_roe_percent"],9.27)
        for r in found.values():
            self.assertIsNone(r["per_reference"])
            self.assertIsNone(r["pbr_reference_unverified"])
            self.assertFalse(r["ranking_eligible"])
            self.assertTrue(r["banking_indicators"]["not_bank_reported_roe"])
        self.assertNotIn("banking_indicators",feed["records"][0])

    def test_missing_verified_bank_scope_skipped(self):
        feed=sample()
        feed["records"][2].pop("banking_audited")
        out=compute_bank_indicators(feed)
        self.assertNotIn("banking_indicators",out["records"][2])

    def test_missing_equity_rejected(self):
        feed=sample()
        del feed["records"][0]["banking_evidence"]["balance"]["2025"]["parent_shareholders_funds"]
        with self.assertRaises(ValueError):compute_bank_indicators(feed)

    def test_unverified_valuation_rejected(self):
        feed=sample()
        feed["records"][1]["price_sgd"]=12.0
        with self.assertRaises(ValueError):compute_bank_indicators(feed)

    def test_bad_costs_rejected(self):
        feed=sample()
        feed["records"][2]["banking_audited"]["income"]["total_operating_expenses"]["2025"]=999999
        with self.assertRaises(ValueError):compute_bank_indicators(feed)

    def test_other_sgx_records_unchanged(self):
        feed=sample()
        feed["records"].append({"symbol":"S68","ranking_eligible":False,"market_cap_sgd":5})
        out=compute_bank_indicators(feed)
        self.assertEqual(out["records"][-1],feed["records"][-1])

if __name__=="__main__":
    unittest.main()
