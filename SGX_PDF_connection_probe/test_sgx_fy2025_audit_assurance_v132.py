import copy,unittest
from sgx_fy2025_audit_assurance_v132 import combine
def docs():
 rows=[{"symbol":s,"fiscal_year":2025,"ranking_eligible":False,
        "financial_pdf_sha256":"a"*64,"financial_source_url":"https://links.sgx.com/FileOpen/official",
        "revenue_sgd_thousands":2452053 if s=="G13" else 12346426}
       for s in ("G13","S63","S68","S20","D05","O39","U11")]
 feed={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
       "ranking_enabled":False,"records":rows,"updated_at_utc":"2026-11-14T00:00:00Z"}
 originals={}
 for sym in ("G13","S63"):
  g=sym=="G13"
  record={"schema_version":"sgx-g13-fy2025-independent-auditor-opinion-v130" if g else "sgx-s63-fy2025-independent-audit-proof-v131",
          "symbol":sym,"source_url":"https://links.sgx.com/FileOpen/official",
          "source_pdf_sha256":"a"*64,
          "auditor_document_sha256":"a"*64,
          "auditor_issuer":"PricewaterhouseCoopers LLP","auditor":"PricewaterhouseCoopers LLP",
          "audited_annual_group_financials_period_end":"2025-12-31",
          "audit_reporting_period_end":"2025-12-31",
          "auditor_independence_statement_observed":True,
          "auditor_independence_statement_verified":True,
          "independent_auditor_opinion_found":True,
          "audit_opinion_scope_verified":True,
          "ranking_eligible":False,"financial_feed_modified":False,
          "reported_annual_revenue_sgd_thousands":2452053,
          "auditor_KAM_mentions_revenue_sgd":12346426000,
          "published_revenue_matches_auditor_KAM":True}
  originals[sym]={"schema_version":"sgx-g13-fy2025-auditor-probe-v130" if g else "sgx-s63-auditor-probe-v131",
   "status":"INDEPENDENT_FY2025_AUDITOR_OPINION_IN_PRIMARY_PDF_CONFIRMED" if g else "SGX_INDEPENDENT_S63_FY2025_AUDITOR_REPORT_CONFIRMED",
   "record":record}
 return feed,originals
class Tests(unittest.TestCase):
 def test_two_audits_do_not_promote(self):
  f,o=docs();original=copy.deepcopy(f)
  a=combine(f,o)
  self.assertEqual(a["external_auditor_fy2025_opinion_confirmed_count"],2)
  self.assertEqual(a["numeric_recalculation_completed_count"],0)
  self.assertEqual(a["ranking_eligible_count"],0)
  self.assertEqual(f,original)
 def test_forged_or_2026_opinion_rejected(self):
  for mutate in [
   lambda f,o:o["S63"]["record"].update(auditor_independence_statement_verified=False),
   lambda f,o:o["G13"]["record"].update(source_pdf_sha256="b"*64),
   lambda f,o:f["records"][1].update(revenue_sgd_thousands=100),
   lambda f,o:f.update(ranking_eligible_count=1),
   lambda f,o:o["S63"].update(status="NOT_VERIFIED")]:
   f,o=docs();mutate(f,o)
   with self.assertRaises(ValueError):combine(f,o)
if __name__=="__main__":unittest.main()
