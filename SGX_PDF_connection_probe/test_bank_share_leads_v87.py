"""v87: new SGXNet event must not erase older event or become market valuation."""
import unittest
from bank_share_leads_v87 import update,STATUS
from bank_share_leads_v83 import annotate as annotate_v83

def sample():
 return annotate_v83({"schema_version":"value_hunter_web_v29",
 "records":[{"symbol":s,"ranking_eligible":False,
   "bank_financial_state":{"status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"},
   "bank_historical_shares":{"as_of_date":"2026-02-23" if s=="U11" else "2026-02-25"},
   "shares_outstanding":None,"price_sgd":None,"market_cap_sgd":None,
   "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None}
 for s in ("U11","O39")]})

class Tests(unittest.TestCase):
 def test_preserves_september_while_newer_november_lead_is_unverified(self):
  feed=sample();out=update(feed)
  uob=out["records"][0]
  self.assertEqual(uob["bank_share_discovery_history"][0]["event_date"],"2026-09-30")
  self.assertEqual(uob["bank_share_discovery_history"][0]["candidate_shares_excluding_treasury"],1647838591)
  self.assertEqual(uob["bank_share_discovery"]["event_date"],"2026-11-13")
  self.assertEqual(uob["bank_share_discovery"]["candidate_shares_excluding_treasury"],1646677591)
  self.assertEqual(uob["bank_share_discovery"]["candidate_treasury_shares"],14548000)
  self.assertEqual(uob["bank_share_discovery"]["status"],STATUS)
  self.assertIsNone(uob["bank_share_discovery"]["primary_sgx_announcement_url"])
  self.assertFalse(uob["bank_share_discovery"]["current_share_count_usable"])
  self.assertFalse(uob["bank_share_discovery"]["ranking_eligible"])
  self.assertIsNone(uob["shares_outstanding"])
  self.assertIsNone(uob["price_sgd"])
  self.assertEqual(out["records"][1],feed["records"][1])
  self.assertNotIn("bank_share_discovery_history",feed["records"][0])
 def test_unknown_september_event_rejected(self):
  f=sample();f["records"][0]["bank_share_discovery"]["candidate_treasury_shares"]+=1
  with self.assertRaises(ValueError):update(f)
 def test_priced_bank_rejected(self):
  f=sample();f["records"][0]["price_sgd"]=37
  with self.assertRaises(ValueError):update(f)
 def test_missing_source_status_rejected(self):
  f=sample();f["records"][0]["bank_share_discovery"]["status"]="PRIMARY_CONFIRMED"
  with self.assertRaises(ValueError):update(f)
 def test_does_not_claim_november_is_latest_official(self):
  f=sample();out=update(f)
  lead=out["records"][0]["bank_share_discovery"]
  self.assertTrue(lead["discovered_event_not_proof_of_latest"])
  self.assertFalse(lead["primary_issuer_count_reconciled"])
if __name__=="__main__":unittest.main()
