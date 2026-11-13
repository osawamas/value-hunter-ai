"""v89: published primary UOB Nov-12 cannot override newer secondary Nov-13 or live shares."""
import unittest
from u11_nov12_publish_v89 import attach,STATUS
from u11_nov12_primary_v88 import URL,REF,DATE

def fixtures():
 feed={"schema_version":"value_hunter_web_v29","records":[{
  "symbol":"U11","ranking_eligible":False,
  "bank_primary_share_history":{"status":"ORIGINAL_SGX_DAILY_BUYBACK_2026_09_07_RECONCILED",
                                "as_of_date":"2026-09-07"},
  "bank_share_discovery":{"status":"SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED",
                          "event_date":"2026-11-13","current_share_count_usable":False},
  "bank_share_discovery_history":[{"event_date":"2026-09-30"}],
  "shares_outstanding":None,"price_sgd":None,"market_cap_sgd":None,
  "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None}]}
 source={"symbol":"U11","status":STATUS,"source_url":URL,
  "record":{"symbol":"U11","status":"DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY",
   "reference":REF,"as_of_date":DATE,"source_url":URL,
   "primary_sgx_page_sha256":"a"*64,
   "issued_excluding_treasury":1646711591,
   "treasury_shares":14548000,
   "issued_including_treasury_derived":1661259591,
   "ranking_eligible":False,"valuation_eligible":False,"not_proof_of_latest":True}}
 return feed,source

class UOBNov12PublishingTests(unittest.TestCase):
 def test_verified_nov12_is_past_primary_source_only(self):
  feed,source=fixtures()
  out=attach(feed,source)
  row=out["records"][0]
  self.assertEqual(row["bank_primary_recent_share_event"]["issued_excluding_treasury"],1646711591)
  self.assertTrue(row["bank_primary_recent_share_event"]["later_2026_11_13_notification_primary_unverified"])
  self.assertTrue(row["bank_primary_recent_share_event"]["not_proof_of_current_shares"])
  self.assertEqual(row["bank_primary_share_history"]["as_of_date"],"2026-09-07")
  self.assertEqual(row["bank_share_discovery"]["event_date"],"2026-11-13")
  self.assertEqual(row["bank_share_discovery_history"][0]["event_date"],"2026-09-30")
  self.assertIsNone(row["shares_outstanding"])
  self.assertIsNone(row["price_sgd"])
  self.assertIsNone(row["market_cap_sgd"])
  self.assertFalse(row["ranking_eligible"])
  self.assertNotIn("bank_primary_recent_share_event",feed["records"][0])
 def test_falsified_sgx_page_digest_rejected(self):
  f,s=fixtures();s["record"]["primary_sgx_page_sha256"]="bad"
  with self.assertRaises(ValueError):attach(f,s)
 def test_changed_shares_rejected(self):
  f,s=fixtures();s["record"]["treasury_shares"]+=1
  with self.assertRaises(ValueError):attach(f,s)
 def test_wrong_notice_reference_rejected(self):
  f,s=fixtures();s["record"]["reference"]="SG261113OTHRHOAF"
  with self.assertRaises(ValueError):attach(f,s)
 def test_missing_prior_record_rejected(self):
  f,s=fixtures();f["records"][0].pop("bank_primary_share_history")
  with self.assertRaises(ValueError):attach(f,s)
 def test_later_event_not_reconciled_rejected(self):
  f,s=fixtures();f["records"][0]["bank_share_discovery"]["status"]="PRIMARY_CONFIRMED"
  with self.assertRaises(ValueError):attach(f,s)
 def test_valuation_injection_rejected(self):
  f,s=fixtures();f["records"][0]["price_sgd"]=37.8
  with self.assertRaises(ValueError):attach(f,s)
if __name__=="__main__":unittest.main()
