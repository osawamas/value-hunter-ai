"""v92: consistency of secondary buyback claim != original SGX verification."""
import copy
import unittest
from u11_pending_buyback_v92 import attach,STATUS

def fixture():
    p={"status":"ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED",
       "as_of_date":"2026-11-12","issued_excluding_treasury":1646711591,
       "treasury_shares":14548000,
       "primary_html_sha256":"a"*64,
       "primary_source_url":"https://links.sgx.com/1.0.0/corporate-announcements/MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d"}
    chain={"status":"ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED",
           "records":[{"as_of_date":"2026-11-10"},
                      {"as_of_date":"2026-11-11"},
                      {"as_of_date":"2026-11-12","issued_excluding_treasury":1646711591,
                       "official_html_sha256":"a"*64}]}
    lead={"status":"SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED",
          "claim_source_class":"SECONDARY_SGXNET_SYNDICATION",
          "event_date":"2026-11-13",
          "sgx_announcement_reference":"SG261113OTHRHOAF",
          "candidate_shares_excluding_treasury":1646677591,
          "candidate_treasury_shares":14548000,
          "primary_sgx_announcement_url":None,
          "primary_document_sha256":None,
          "primary_issuer_count_reconciled":False,
          "secondary_source_url":"https://classic.shareinvestor.com/news/news.html?nid=515671689&source=regional_sgxnet"}
    return {"schema_version":"value_hunter_web_v29","records":[{
        "symbol":"U11","ranking_eligible":False,
        "bank_primary_recent_share_event":p,"bank_primary_three_day_chain":chain,
        "bank_share_discovery":lead,"shares_outstanding":None,"price_sgd":None,
        "market_cap_sgd":None,"per_reference":None,
        "pbr_reference_unverified":None,"pbr_verified":None},
        {"symbol":"O39","ranking_eligible":False}]}

class Tests(unittest.TestCase):
    def test_consistent_secondary_claim_stays_unverified(self):
        src=fixture();out=attach(src)
        u=out["records"][0]
        status=u["bank_pending_buyback_consistency"]
        self.assertEqual(status["status"],STATUS)
        self.assertEqual(status["implied_share_decrease"],34000)
        self.assertFalse(status["latest_current_shares_verified"])
        self.assertFalse(status["current_share_count_usable"])
        self.assertFalse(status["market_cap_per_pbr_usable"])
        self.assertIsNone(status["secondary_primary_url"])
        self.assertIsNone(u["shares_outstanding"])
        self.assertIsNone(u["market_cap_sgd"])
        self.assertFalse(u["ranking_eligible"])
        self.assertNotIn("bank_pending_buyback_consistency",src["records"][0])
        self.assertEqual(out["records"][1],src["records"][1])
    def test_forged_secondary_original_url_rejected(self):
        x=fixture();x["records"][0]["bank_share_discovery"]["primary_sgx_announcement_url"]="https://links.sgx.com/1.0.0/corporate-announcements/FAKE/"
        with self.assertRaises(ValueError):attach(x)
    def test_wrong_count_rejected(self):
        x=fixture();x["records"][0]["bank_share_discovery"]["candidate_shares_excluding_treasury"]+=100
        with self.assertRaises(ValueError):attach(x)
    def test_mismatched_primary_sha_rejected(self):
        x=fixture();x["records"][0]["bank_primary_three_day_chain"]["records"][-1]["official_html_sha256"]="b"*64
        with self.assertRaises(ValueError):attach(x)
    def test_wrong_recent_date_rejected(self):
        x=fixture();x["records"][0]["bank_share_discovery"]["event_date"]="2026-11-14"
        with self.assertRaises(ValueError):attach(x)
    def test_new_valuation_rejected(self):
        x=fixture();x["records"][0]["price_sgd"]=37.75
        with self.assertRaises(ValueError):attach(x)
    def test_wrong_issuer_group_rejected(self):
        x=fixture();x["records"][0]["symbol"]="O39"
        with self.assertRaises(ValueError):attach(x)
if __name__=="__main__":unittest.main()
