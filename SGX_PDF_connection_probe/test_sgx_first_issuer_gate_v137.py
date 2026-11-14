import copy,unittest
from sgx_first_issuer_gate_v137 import assess,REQUIRED
def docs():
 f={"schema_version":"value_hunter_web_v29","ranking_enabled":False,"ranking_eligible_count":0,
    "updated_at_utc":"2026-11-14T00:00:00Z","records":[]}
 for s in ("G13","S63","S68","S20","D05","O39","U11"):
  f["records"].append({"symbol":s,"issuer":s,"ranking_eligible":False,"ranking_score":None,
   "fiscal_year":2025,"financial_pdf_sha256":"a"*64,"financial_source_url":"https://links.sgx.com/annual",
   "quote_source_type":"YAHOO_FINANCE_UNOFFICIAL_CHART"})
 a={"schema_version":"sgx-fy2025-audit-assurance-v132","linked_published_feed_updated_at_utc":f["updated_at_utc"],
    "external_auditor_fy2025_opinion_confirmed_count":2,"numeric_recalculation_completed_count":0,
    "ranking_eligible_count":0,"financial_feed_modified":False,"records":[]}
 for s in ("G13","S63"):
  a["records"].append({"symbol":s,"fiscal_year":2025,
   "annual_report_primary_sha256":"a"*64,"annual_report_primary_source_url":"https://links.sgx.com/annual",
   "independent_external_audit_opinion_observed":True,"auditor":"PricewaterhouseCoopers LLP",
   "auditor_scope_end":"2025-12-31","reperformed_independent_financial_calculations":False,
   "parent_equity_independently_reperformed":False,
   "current_shares_and_quote_independently_verified":False,"eligible_for_ranking":False})
 g={"schema_version":"sgx-g13-h1-direct-primary-share-confirmation-v127",
    "published_june30_count_original_primary_supported":True,"shares_after_june30_unchanged_verified":False,
    "issued_ex_treasury_at_june30":12063642274,"ranking_eligible":False}
 s={"schema_version":"sgx-share-snapshot-difference-v110","symbol":"S63",
    "new_sgx_primary_snapshot_date":"2026-11-13","current_shares_verified":False,
    "price_or_per_pbr_recomputed":False,"ranking_eligible":False,
    "new_sgx_primary_issued_ex_treasury":3115847115}
 q={"schema_version":"sgx-s63-historical-close-second-website-v129",
    "primary_exchange_execution_quote_verified":False,
    "upstream_market_data_provider_independence_verified":False,"ranking_eligible":False}
 return f,a,g,s,q
class Tests(unittest.TestCase):
 def test_all_requirements_explicit_and_ranking_still_zero(self):
  inputs=docs();before=copy.deepcopy(inputs)
  x=assess(*inputs)
  self.assertEqual(len(x["records"]),2)
  self.assertEqual(x["eligible_count"],0)
  self.assertFalse(x["ranking_activation_permitted"])
  self.assertEqual(inputs,before)
  for r in x["records"]:
   self.assertEqual(set(r["evidence_requirements"]),set(REQUIRED))
   self.assertEqual(set(r["unmet_requirements"]),set(REQUIRED)-{"fy2025_external_auditor_opinion"})
   self.assertFalse(r["eligible_for_ranking"])
 def test_forged_or_stale_record_rejected(self):
  changes=[
   lambda x:x[0].update(ranking_eligible_count=1),
   lambda x:x[1].update(linked_published_feed_updated_at_utc="stale"),
   lambda x:x[0]["records"][0].update(financial_pdf_sha256="b"*64),
   lambda x:x[1]["records"][1].update(reperformed_independent_financial_calculations=True),
   lambda x:x[2].update(shares_after_june30_unchanged_verified=True),
   lambda x:x[3].update(new_sgx_primary_issued_ex_treasury=1),
   lambda x:x[4].update(primary_exchange_execution_quote_verified=True),
   lambda x:x[0]["records"][0].update(ranking_eligible=True)
  ]
  for update in changes:
   inputs=list(docs());update(inputs)
   with self.assertRaises(ValueError):assess(*inputs)
if __name__=="__main__":unittest.main()
