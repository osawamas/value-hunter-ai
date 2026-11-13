"""v91: audited three-day SGX chain must not become current UOB shares."""
import unittest
from u11_buyback_chain_publish_v91 import attach,STATUS
from u11_buyback_chain_v90 import NOTICES

def sample():
 events=[]
 for day,ref,url,net,treasury in NOTICES:
  events.append({"symbol":"U11","status":"DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY",
   "reference":ref,"as_of_date":day,"source_url":url,
   "issued_excluding_treasury":net,"treasury_shares":treasury,
   "issued_including_treasury_derived":net+treasury,
   "not_proof_of_latest":True,"valuation_eligible":False,
   "primary_sgx_page_sha256":("a" if day!="2026-11-12" else "b")*64})
 feed={"schema_version":"value_hunter_web_v29","records":[
  {"symbol":"U11","ranking_eligible":False,"price_sgd":None,
   "shares_outstanding":None,"market_cap_sgd":None,"per_reference":None,
   "pbr_reference_unverified":None,"pbr_verified":None,
   "bank_primary_recent_share_event":{"status":"ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED",
      "primary_html_sha256":"b"*64,"issued_excluding_treasury":1646711591},
   "bank_share_discovery":{"status":"SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED",
      "event_date":"2026-11-13","current_share_count_usable":False}},
  {"symbol":"O39","ranking_eligible":False}]}
 proof={"symbol":"U11","status":STATUS,"record":{
  "symbol":"U11","status":STATUS,"records":events,
  "treasury_constant":True,"consecutive_day_net_decrease":34000,
  "latest_primary_in_chain":"2026-11-12",
  "later_2026_11_13_claim_verified":False,
  "not_proof_of_latest_as_of_today":True,
  "current_market_cap_eligible":False,"ranking_eligible":False}}
 return feed,proof

class Tests(unittest.TestCase):
 def test_three_day_verified_chain_remains_historical(self):
  f,p=sample();result=attach(f,p)
  bank=result["records"][0]
  chain=bank["bank_primary_three_day_chain"]
  self.assertEqual(len(chain["records"]),3)
  self.assertEqual(chain["net_decrease_each_consecutive_day"],34000)
  self.assertFalse(chain["2026_11_13_original_verified"])
  self.assertFalse(chain["market_cap_eligible"])
  self.assertIsNone(bank["shares_outstanding"])
  self.assertIsNone(bank["price_sgd"])
  self.assertFalse(bank["ranking_eligible"])
  self.assertNotIn("bank_primary_three_day_chain",f["records"][0])
  self.assertEqual(result["records"][1],f["records"][1])
 def test_one_original_missing_rejected(self):
  f,p=sample();p["record"]["records"].pop(1)
  with self.assertRaises(ValueError):attach(f,p)
 def test_original_hash_conflicts_with_nov12_snapshot(self):
  f,p=sample();p["record"]["records"][2]["primary_sgx_page_sha256"]="c"*64
  with self.assertRaises(ValueError):attach(f,p)
 def test_middle_day_shares_changed(self):
  f,p=sample();p["record"]["records"][1]["issued_excluding_treasury"]+=100
  with self.assertRaises(ValueError):attach(f,p)
 def test_nov13_is_not_primary(self):
  f,p=sample();p["record"]["later_2026_11_13_claim_verified"]=True
  with self.assertRaises(ValueError):attach(f,p)
 def test_quote_injected_rejected(self):
  f,p=sample();f["records"][0]["price_sgd"]=36
  with self.assertRaises(ValueError):attach(f,p)
if __name__=="__main__":unittest.main()
