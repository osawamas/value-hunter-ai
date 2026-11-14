"""v99: third-party company candidates never overwrite 7 verified issuers."""
import json,unittest
from sgx_companies_api_v98 import parse
from sgx_companies_publish_v99 import publish
from test_sgx_companies_api_v98 import sample

def source():
 return parse(sample())

def verified():
 return {"schema_version":"value_hunter_web_v29","records":[
  {"symbol":s,"price_sgd":None,"ranking_eligible":False}
  for s in ("S68","G13","S20","S63","D05","O39","U11")]}

class TestPublishing(unittest.TestCase):
 def test_separate_partial_directory_only(self):
  feed=verified();out=publish(feed,source())
  self.assertEqual(out["provider_accepted_candidate_count"],62)
  self.assertEqual(out["known_verified_issuer_overlap"],7)
  self.assertEqual(out["known_verified_issuer_missing"],[])
  self.assertEqual(out["coverage"],"PARTIAL_UNVERIFIED")
  self.assertFalse(out["eligible_for_ranking"])
  self.assertTrue(out["records_not_added_to_verified_financial_feed"])
  self.assertTrue(out["candidates"][0]["source_verification"].startswith("THIRD_PARTY"))
  self.assertNotIn("candidates",feed)
  self.assertEqual(len(feed["records"]),7)
  self.assertNotIn("market_cap_sgd",out["candidates"][0])
 def test_missing_company_source_overlap_visible(self):
  s=parse(sample(missing_symbols=True))
  out=publish(verified(),s)
  self.assertEqual(out["known_verified_issuer_missing"],["U11"])
  self.assertEqual(out["known_verified_issuer_overlap"],6)
 def test_incorrect_hash_rejected(self):
  s=source();s["source_response_sha256"]="fake"
  with self.assertRaises(ValueError):publish(verified(),s)
 def test_completeness_forged_rejected(self):
  s=source();s["all_sgx_listings_verified"]=True
  with self.assertRaises(ValueError):publish(verified(),s)
 def test_candidate_cannot_duplicate_symbol(self):
  s=source();s["companies"].append(s["companies"][0].copy())
  s["accepted_candidates"]+=1
  with self.assertRaises(ValueError):publish(verified(),s)
 def test_missing_original_feed_record_rejected(self):
  f=verified();f["records"].pop()
  with self.assertRaises(ValueError):publish(f,source())
 def test_changed_candidate_symbol_rejected(self):
  s=source();s["companies"][0]["symbol"]="../bad"
  with self.assertRaises(ValueError):publish(verified(),s)
 def test_provider_metadata_inconsistent_rejected(self):
  s=source();s["known_symbols_present"].remove("U11")
  with self.assertRaises(ValueError):publish(verified(),s)

if __name__=="__main__":unittest.main()
