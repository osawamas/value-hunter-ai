"""v86: historical first-party UOB snapshot must never be used as live shares."""
import unittest
from u11_primary_publish_v86 import attach,STATUS
from u11_primary_snapshot_v85 import URL,REF,DATE

def fixtures():
 feed={"schema_version":"value_hunter_web_v29","records":[
  {"symbol":"U11","ranking_eligible":False,
   "bank_share_discovery":{"event_date":"2026-09-30","status":"SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"},
   "price_sgd":None,"shares_outstanding":None,"market_cap_sgd":None,
   "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None},
  {"symbol":"O39","ranking_eligible":False}]}
 proof={"symbol":"U11","status":STATUS,"source_url":URL,
        "record":{"symbol":"U11","status":"DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY",
          "reference":REF,"as_of_date":DATE,"source_url":URL,
          "primary_sgx_page_sha256":"a"*64,
          "issued_excluding_treasury":1648956591,"treasury_shares":14160900,
          "issued_including_treasury_derived":1663117491,
          "not_proof_of_latest":True,
          "requires_additional_events_and_crosscheck":True,
          "valuation_eligible":False,"ranking_eligible":False}}
 return feed,proof

class DirectSGXPublishingTests(unittest.TestCase):
 def test_sgx_history_preserves_fresher_secondary_disclosure(self):
  feed,proof=fixtures()
  out=attach(feed,proof)
  uob=out["records"][0]
  self.assertEqual(uob["bank_primary_share_history"]["issued_excluding_treasury"],1648956591)
  self.assertTrue(uob["bank_primary_share_history"]["historical_only"])
  self.assertTrue(uob["bank_primary_share_history"]["subsequent_corporate_actions_not_reconciled"])
  self.assertEqual(uob["bank_share_discovery"]["event_date"],"2026-09-30")
  self.assertIsNone(uob["shares_outstanding"])
  self.assertIsNone(uob["price_sgd"])
  self.assertFalse(uob["ranking_eligible"])
  self.assertNotIn("bank_primary_share_history",feed["records"][0])
  self.assertEqual(out["records"][1],feed["records"][1])
 def test_invalid_origin_ref_blocked(self):
  f,p=fixtures();p["record"]["reference"]="SG261113OTHRHOAF"
  with self.assertRaises(ValueError):attach(f,p)
 def test_current_price_cannot_be_overwritten(self):
  f,p=fixtures();f["records"][0]["price_sgd"]=44
  with self.assertRaises(ValueError):attach(f,p)
 def test_changed_gross_rejected(self):
  f,p=fixtures();p["record"]["issued_including_treasury_derived"]+=1
  with self.assertRaises(ValueError):attach(f,p)
 def test_mismatched_document_source_rejected(self):
  f,p=fixtures();p["record"]["source_url"]="https://evil.example/buyback"
  with self.assertRaises(ValueError):attach(f,p)
 def test_later_history_is_not_latest_verified(self):
  f,p=fixtures();f["records"][0]["bank_share_discovery"]["event_date"]="2026-09-01"
  with self.assertRaises(ValueError):attach(f,p)
 def test_failed_source_does_not_publish(self):
  f,p=fixtures();p["status"]="NOT_VERIFIED"
  with self.assertRaises(ValueError):attach(f,p)

if __name__=="__main__":unittest.main()
