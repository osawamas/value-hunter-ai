"""v83: secondary SGXNet disclosure lead cannot become current shares or valuation."""
import unittest
from bank_share_leads_v83 import annotate,STATUS,LEADS

def fixture():
 return {"schema_version":"value_hunter_web_v29",
         "records":[{"symbol":sym,"ranking_eligible":False,
           "bank_financial_state":{"status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"},
           "bank_historical_shares":{"as_of_date":"2026-02-23" if sym=="U11" else "2026-02-25"},
           "shares_outstanding":None,"price_sgd":None,"market_cap_sgd":None,
           "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None}
           for sym in ("O39","U11")]+[{"symbol":"D05","ranking_eligible":False}]}

class LeadsTest(unittest.TestCase):
 def test_all_discovered_events_are_unverified(self):
  src=fixture();out=annotate(src)
  for r in out["records"][:2]:
   lead=r["bank_share_discovery"]
   self.assertEqual(lead["status"],STATUS)
   self.assertIsNone(lead["primary_sgx_announcement_url"])
   self.assertFalse(lead["primary_issuer_count_reconciled"])
   self.assertFalse(lead["current_share_count_usable"])
   self.assertFalse(lead["market_cap_per_pbr_usable"])
   self.assertIsNone(r["shares_outstanding"])
   self.assertIsNone(r["price_sgd"])
   self.assertFalse(r["ranking_eligible"])
  self.assertEqual(out["records"][1]["bank_share_discovery"]["candidate_shares_excluding_treasury"],1647838591)
  self.assertIsNone(out["records"][0]["bank_share_discovery"]["candidate_shares_excluding_treasury"])
  self.assertNotIn("bank_share_discovery",out["records"][2])
  self.assertNotIn("bank_share_discovery",src["records"][0])
 def test_source_event_is_not_marked_as_latest(self):
  r=annotate(fixture())["records"][1]["bank_share_discovery"]
  self.assertTrue(r["discovered_event_not_proof_of_latest"])
 def test_existing_price_rejected(self):
  f=fixture();f["records"][1]["price_sgd"]=42
  with self.assertRaises(ValueError):annotate(f)
 def test_existing_current_shares_rejected(self):
  f=fixture();f["records"][1]["shares_outstanding"]=1
  with self.assertRaises(ValueError):annotate(f)
 def test_missing_audited_financial_status_rejected(self):
  f=fixture();f["records"][0].pop("bank_financial_state")
  with self.assertRaises(ValueError):annotate(f)
 def test_more_recent_verified_shares_cannot_be_overwritten(self):
  f=fixture();f["records"][1]["bank_historical_shares"]["as_of_date"]="2026-10-01"
  with self.assertRaises(ValueError):annotate(f)
 def test_nonbank_preserved(self):
  f=fixture();f["records"].append({"symbol":"S68","price_sgd":1.5})
  r=annotate(f)
  self.assertEqual(r["records"][-1],f["records"][-1])

if __name__=="__main__":unittest.main()
