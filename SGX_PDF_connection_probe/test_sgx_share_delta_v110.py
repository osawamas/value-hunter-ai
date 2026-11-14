"""v110: ensure the newer S63 SGX primary share snapshot never silently revalues the feed."""
import copy
import unittest
from sgx_share_delta_v110 import reconcile

def inputs():
    feed={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
          "ranking_enabled":False,"records":[
              {"symbol":"S63","shares_outstanding":3119304988,
               "shares_count_basis":"issued_excluding_treasury",
               "shares_as_of_date":"2026-06-30","price_sgd":9.67,
               "market_cap_sgd":30163679233.96,"ranking_eligible":False}]}
    rec={"status":"SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT",
         "reference":"SG261113OTHRPXGV","symbol":"S63","isin":"SG1F60858221",
         "purchase_date":"2026-11-13","source_url":"https://links.sgx.com/official",
         "source_sha256":"a"*64,"dated_historical_snapshot_only":True,
         "allow_market_cap_or_per_pbr":False,"ranking_eligible":False,
         "shares_purchased":500000,"shares_cancelled":0,"purchased_as_treasury":500000,
         "issued_excluding_treasury_after_purchase":3115847115,
         "treasury_shares_after_purchase":6648082}
    evidence={"schema_version":"sgx-s63-buyback-original-v109",
              "status":"SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT",
              "source_url":"https://links.sgx.com/official","record":rec}
    return feed,evidence

class ShareDeltaTests(unittest.TestCase):
    def test_dated_difference_keeps_financial_feed_unchanged(self):
        feed,evidence=inputs()
        original=copy.deepcopy(feed)
        x=reconcile(feed,evidence)
        self.assertEqual(x["new_minus_published_shares"],-3457873)
        self.assertEqual(x["new_sgx_primary_issued_ex_treasury"],3115847115)
        self.assertTrue(x["published_reference_is_older"])
        self.assertFalse(x["current_shares_verified"])
        self.assertFalse(x["price_or_per_pbr_recomputed"])
        self.assertFalse(x["ranking_eligible"])
        self.assertEqual(feed,original)
    def test_reject_forged_source(self):
        feed,evidence=inputs()
        for field,bad in [("reference","FAKE"),("isin","FAKE"),
                          ("issued_excluding_treasury_after_purchase",0),
                          ("shares_cancelled",10),("ranking_eligible",True)]:
            altered=copy.deepcopy(evidence);altered["record"][field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):
                reconcile(feed,altered)
    def test_reject_old_or_wrong_basis(self):
        feed,evidence=inputs()
        feed["records"][0]["shares_as_of_date"]="2026-11-14"
        with self.assertRaises(ValueError):reconcile(feed,evidence)
        feed["records"][0]["shares_as_of_date"]="2026-06-30"
        feed["records"][0]["shares_count_basis"]="gross_issued"
        with self.assertRaises(ValueError):reconcile(feed,evidence)
    def test_reject_already_ranked(self):
        feed,evidence=inputs()
        feed["ranking_eligible_count"]=1
        with self.assertRaises(ValueError):reconcile(feed,evidence)

if __name__=="__main__":
    unittest.main()
