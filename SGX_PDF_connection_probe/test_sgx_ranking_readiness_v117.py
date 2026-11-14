import unittest
from sgx_ranking_readiness_v117 import audit, SYMBOLS
def fixtures():
 r=[]
 for s in SYMBOLS:
  bank=s in ("D05","O39","U11")
  x={"symbol":s,"ranking_eligible":False,"ranking_score":None,"data_state":"PARTIAL_UNVERIFIED",
    "exclusion_reasons":["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"]}
  if bank:
   x["bank_financial_state"]={"status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED",
     "banking_metrics_parsed":True,"pdf_sha256":"a"*64,
     "third_party_numerical_verification":False,"current_quote_verified":False,
     "current_share_count_verified":False}
  else:
   x.update({"financial_pdf_sha256":"a"*64,"financial_source_url":"https://example.org/official.pdf",
      "audit_states":{"revenue":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT",
       "attributable_profit":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT"},
      "attributable_profit_sgd_thousands":100})
  r.append(x)
 return ({"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
   "ranking_enabled":False,"updated_at_utc":"2026-11-14T00:00:00Z","records":r},
   {"record":{"symbol":"S63","reference":"SG261113OTHRPXGV",
      "purchase_date":"2026-11-13","dated_historical_snapshot_only":True,
      "ranking_eligible":False}})
class Tests(unittest.TestCase):
 def test_all_seven_remain_ineligible(self):
  f,s=fixtures();x=audit(f,s)
  self.assertEqual(x["ranking_eligible_count"],0)
  self.assertEqual(len(x["records"]),7)
  self.assertTrue(all(not r["eligible_for_ranking"] for r in x["records"]))
  self.assertTrue(x["records"][3]["observed_evidence_signals"]["dated_primary_buyback_snapshot_available"])
 def test_banks_do_not_require_industrial_revenue(self):
  f,s=fixtures()
  x=audit(f,s)
  for r in x["records"][4:]:
   self.assertNotIn("issuer_two_document_revenue_crosscheck",r["observed_evidence_signals"])
   self.assertIn("bank_independent_financial_check",r["remaining_verification_tasks"])
 def test_fail_closed_if_rank_promoted(self):
  f,s=fixtures();f["records"][0]["ranking_eligible"]=True
  with self.assertRaises(ValueError):audit(f,s)
 def test_fail_closed_if_duplicate(self):
  f,s=fixtures();f["records"][6]["symbol"]="D05"
  with self.assertRaises(ValueError):audit(f,s)
 def test_fail_closed_bad_feed_count(self):
  f,s=fixtures();f["ranking_eligible_count"]=1
  with self.assertRaises(ValueError):audit(f,s)
 def test_no_share_snapshot_without_verified_source(self):
  f,s=fixtures();s["record"]["reference"]="FAKE"
  x=audit(f,s)
  self.assertFalse(x["records"][3]["observed_evidence_signals"]["dated_primary_buyback_snapshot_available"])
if __name__=="__main__":
 unittest.main()
