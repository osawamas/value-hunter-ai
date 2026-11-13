"""v80 safe public publisher tests for Q3 and nine months (not FY2025)."""
import copy,unittest
from bank_q3_publish_v80 import attach
from bank_q3_financials_v79 import SCHEMAS,SOURCES,STATUS

def fixtures(symbol):
 source=SOURCES[symbol]
 interim={"symbol":symbol,"status":STATUS,
          "source_url":source["url"],"pdf_sha256":"a"*64,
          "record":{"symbol":symbol,"status":STATUS,
                    "published_at_date":source["released"],
                    "period_end":"2026-09-30","ranking_eligible":False,
                    "independently_verified":False,"not_audited_annual_statement":True}}
 for period,start,duration in (("Q3","2026-07-01","THREE_MONTHS"),("9M","2026-01-01","NINE_MONTHS_YTD")):
  interim["record"][period]={
      "period_start":start,"period_end":"2026-09-30",
      "duration":duration,"unit":"SGD_millions",
      "reporting_scope":"GROUP_ISSUER_TRADING_UPDATE",
      "source_pdf_page":SCHEMAS[symbol]["pages"][period],
      "metrics":{k:(q if period=="Q3" else m) for k,(_,q,m) in SCHEMAS[symbol]["rows"].items()},
  }
 row={"symbol":symbol,"ranking_eligible":False,"financial_source_kind":"REGISTERED_SOURCE_NOT_PARSED",
      "bank_financial_state":{"status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"},
      "banking_evidence":{"existing":"untouched"},"price_sgd":None,
      "shares_outstanding":None,"market_cap_sgd":None,
      "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None}
 return {"schema_version":"value_hunter_web_v29","records":[row]},interim

class InterimPublishTests(unittest.TestCase):
 def test_three_bank_periods_and_previous_evidence_unchanged(self):
  for sym in SCHEMAS:
   feed,proof=fixtures(sym)
   published=attach(feed,proof)
   row=published["records"][0]
   self.assertEqual(row["banking_interim_2026"]["Q3"]["duration"],"THREE_MONTHS")
   self.assertEqual(row["banking_interim_2026"]["nine_months"]["duration"],"NINE_MONTHS_YTD")
   self.assertEqual(row["banking_interim_2026"]["Q3"]["metrics"]["total_income"],SCHEMAS[sym]["rows"]["total_income"][1])
   self.assertEqual(row["banking_evidence"],feed["records"][0]["banking_evidence"])
   self.assertNotIn("banking_interim_2026",feed["records"][0])
   self.assertIsNone(row["price_sgd"])
   self.assertIsNone(row["per_reference"])
   self.assertFalse(row["ranking_eligible"])
 def test_bad_source_sha_rejected(self):
  f,p=fixtures("O39");p["pdf_sha256"]="INVALID"
  with self.assertRaises(ValueError):attach(f,p)
 def test_cross_quarter_period_rejected(self):
  f,p=fixtures("D05");p["record"]["Q3"]["period_start"]="2026-01-01"
  with self.assertRaises(ValueError):attach(f,p)
 def test_wrong_9m_income_rejected(self):
  f,p=fixtures("U11");p["record"]["9M"]["metrics"]["total_income"]=p["record"]["Q3"]["metrics"]["total_income"]
  with self.assertRaises(ValueError):attach(f,p)
 def test_missing_audited_group_state_rejected(self):
  f,p=fixtures("O39");f["records"][0].pop("bank_financial_state")
  with self.assertRaises(ValueError):attach(f,p)
 def test_injected_valuation_rejected(self):
  f,p=fixtures("D05");f["records"][0]["market_cap_sgd"]=12345
  with self.assertRaises(ValueError):attach(f,p)
 def test_disclaimer_required(self):
  f,p=fixtures("U11");p["record"]["independently_verified"]=True
  with self.assertRaises(ValueError):attach(f,p)
if __name__=="__main__":unittest.main()
