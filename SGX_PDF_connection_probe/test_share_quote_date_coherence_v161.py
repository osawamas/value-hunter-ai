import unittest
from share_quote_date_coherence_v161 import reconcile
from datetime import date
def data():
 f={"schema_version":"value_hunter_web_v29","ranking_enabled":False,"ranking_eligible_count":0,
    "updated_at_utc":"2026-11-14T07:08:54+00:00","records":[
    {"symbol":"G13","ranking_eligible":False,"quote_source_type":"YAHOO_FINANCE_UNOFFICIAL_CHART",
     "shares_count_basis":"issued_excluding_treasury","shares_as_of_date":"2026-06-30",
     "quote_timestamp_utc":"2026-11-13T09:13:51+00:00","shares_outstanding":12063642274,
     "shares_pdf_sha256":"a"*64,"shares_source_url":"https://links.sgx.com/issuer"},
    {"symbol":"S63","ranking_eligible":False,"quote_source_type":"YAHOO_FINANCE_UNOFFICIAL_CHART",
     "shares_count_basis":"issued_excluding_treasury","shares_as_of_date":"2026-06-30",
     "quote_timestamp_utc":"2026-11-13T09:11:27+00:00","shares_outstanding":3119304988}]}
 g={"schema_version":"sgx-g13-h1-direct-primary-share-confirmation-v127",
   "published_june30_count_original_primary_supported":True,
   "shares_after_june30_unchanged_verified":False,"ranking_eligible":False,
   "published_share_date":"2026-06-30","issued_ex_treasury_at_june30":12063642274,
   "june30_primary_pdf_sha256":"a"*64,"june30_halfyear_source_url":"https://links.sgx.com/issuer"}
 s={"schema_version":"sgx-share-snapshot-difference-v110",
   "published_reference_is_older":True,"current_shares_verified":False,
   "ranking_eligible":False,"new_sgx_primary_snapshot_date":"2026-11-13",
   "new_sgx_primary_issued_ex_treasury":3115847115,"published_financial_shares":3119304988,
   "published_financial_record_as_of_date":"2026-06-30",
   "new_minus_published_shares":3115847115-3119304988}
 return [f,g,s]
class Test(unittest.TestCase):
 def test_both_are_not_current_marketcap(self):
  a=reconcile(*data())
  self.assertEqual(a["mismatched_reference_date_count"],2)
  self.assertEqual(a["ranking_eligible_count"],0)
  self.assertTrue(all(not x["same_date_reconciled"] for x in a["records"]))
  self.assertGreater(a["records"][0]["share_quote_reference_date_gap_days"],100)
 def test_cannot_promote_s63_old_shares(self):
  f,g,s=data();f["records"][1]["shares_outstanding"]=s["new_sgx_primary_issued_ex_treasury"]
  with self.assertRaises(ValueError):reconcile(f,g,s)
 def test_quote_day_does_not_turn_shares_current(self):
  f,g,s=data();f["records"][0]["shares_as_of_date"]="2026-11-13"
  with self.assertRaises(ValueError):reconcile(f,g,s)
 def test_future_trading_day_does_not_make_june_shares_current(self):
  f,g,s=data()
  f["records"][0]["quote_timestamp_utc"]="2026-11-16T09:13:51+00:00"
  a=reconcile(f,g,s,today=date(2026,11,16))
  self.assertEqual(a["records"][0]["reference_quote_trading_date"],"2026-11-16")
  self.assertFalse(a["records"][0]["same_date_reconciled"])
  self.assertEqual(a["ranking_eligible_count"],0)
 def test_unreasonable_future_quote_rejected(self):
  f,g,s=data()
  f["records"][0]["quote_timestamp_utc"]="2035-01-01T09:13:51+00:00"
  with self.assertRaises(ValueError):reconcile(f,g,s,today=date(2026,11,14))
 def test_ranking_guard(self):
  f,g,s=data();f["ranking_eligible_count"]=1
  with self.assertRaises(ValueError):reconcile(f,g,s)
if __name__=="__main__":unittest.main()
