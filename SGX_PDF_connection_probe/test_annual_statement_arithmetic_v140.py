import unittest
from annual_statement_arithmetic_v140 import calculate
def sample():
 f={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
    "ranking_enabled":False,"updated_at_utc":"2026-11-14T00:00:00Z","records":[]}
 a={"schema_version":"sgx-fy2025-audit-assurance-v132",
    "linked_published_feed_updated_at_utc":f["updated_at_utc"],
    "external_auditor_fy2025_opinion_confirmed_count":2,
    "numeric_recalculation_completed_count":0,"records":[]}
 for symbol,asset,debt,eq,parent in [("G13",9185799,980383,8205416,8205416),
                                     ("S63",16032106,13110861,2921245,2573638)]:
  f["records"].append({"symbol":symbol,"fiscal_year":2025,"ranking_eligible":False,
   "financial_pdf_sha256":"a"*64,"financial_source_url":"https://links.sgx.com/report",
   "assets_sgd_thousands":asset,"liabilities_sgd_thousands":debt,
   "equity_sgd_thousands":eq,"parent_equity_sgd_thousands":parent,
   "attributable_profit_sgd_thousands":390346,
   "balance_difference_sgd_thousands":0,
   "parent_equity_status":"EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED"})
  a["records"].append({"symbol":symbol,
   "annual_report_primary_sha256":"a"*64,"annual_report_primary_source_url":"https://links.sgx.com/report",
   "independent_external_audit_opinion_observed":True,
   "reperformed_independent_financial_calculations":False,
   "parent_equity_independently_reperformed":False})
 return f,a
class Tests(unittest.TestCase):
 def test_calculations_not_external_independence(self):
  x=calculate(*sample())
  self.assertEqual(x["independent_numerical_verification_count"],0)
  self.assertEqual(x["records"][1]["calculated_noncontrolling_interest"],347607)
  self.assertTrue(all(r["ranking_eligible"] is False for r in x["records"]))
 def test_tampered_statement_fails(self):
  for change in [
   lambda f,a:f["records"][0].update(assets_sgd_thousands=100),
   lambda f,a:f["records"][1].update(parent_equity_sgd_thousands=99999999),
   lambda f,a:a.update(linked_published_feed_updated_at_utc="stale"),
   lambda f,a:a["records"][0].update(reperformed_independent_financial_calculations=True),
   lambda f,a:f.update(ranking_eligible_count=1)]:
   f,a=sample();change(f,a)
   with self.assertRaises(ValueError):calculate(f,a)
if __name__=="__main__":unittest.main()
