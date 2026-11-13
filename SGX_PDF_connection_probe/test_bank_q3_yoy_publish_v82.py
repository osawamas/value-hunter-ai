"""v82: reject mismatched bank Q3/9M historical source and tampered returns."""
import copy,unittest
from test_bank_q3_publish_v80 import fixtures
from bank_q3_publish_v80 import attach as publish_quarter
from bank_q3_yoy_publish_v82 import attach,STATUS
from bank_q3_yoy_v81 import COMPARISONS,SOURCES

def inputs(symbol):
 feed,base=fixtures(symbol)
 feed=publish_quarter(feed,base)
 prof=COMPARISONS[symbol]
 rec={"symbol":symbol,"status":STATUS,"released_at_date":SOURCES[symbol]["released"],
      "independent_verification":False,"ranking_eligible":False}
 for period,name,start,prevstart,duration in (
    ("Q3","q3","2026-07-01","2025-07-01","THREE_MONTHS"),
    ("9M","nine_months","2026-01-01","2025-01-01","NINE_MONTHS_YTD")):
  current={k:base["record"][period]["metrics"][k] for k in ("total_income",prof["profit_key"])}
  prior=prof["prior"][period].copy()
  rec[name]={
    "period_end_2026":"2026-09-30","period_end_2025":"2025-09-30",
    "period_start_2026":start,"period_start_2025":prevstart,
    "duration":duration,"unit":"SGD_millions",
    "pdf_page_number":base["record"][period]["source_pdf_page"],
    "current_year":current,"prior_year":prior,
    "growth_pct":{k:round(100*(current[k]/prior[k]-1),2) for k in current},
  }
 proof={"symbol":symbol,"status":STATUS,"source_url":base["source_url"],
        "pdf_sha256":base["pdf_sha256"],"record":rec}
 return feed,proof

class PeriodYoYPublishingTests(unittest.TestCase):
 def test_all_three_banks_source_matched(self):
  for symbol in COMPARISONS:
   feed,proof=inputs(symbol)
   result=attach(feed,proof)
   row=result["records"][0]
   self.assertEqual(row["banking_yoy_2026"]["Q3"]["duration"],"THREE_MONTHS")
   self.assertEqual(row["banking_yoy_2026"]["nine_months"]["duration"],"NINE_MONTHS_YTD")
   self.assertIsNone(row["per_reference"])
   self.assertIsNone(row["market_cap_sgd"])
   self.assertFalse(row["ranking_eligible"])
   self.assertNotIn("banking_yoy_2026",feed["records"][0])
 def test_source_sha_mismatch_rejected(self):
  feed,proof=inputs("O39");proof["pdf_sha256"]="b"*64
  with self.assertRaises(ValueError):attach(feed,proof)
 def test_q3_replaced_with_9m_rejected(self):
  feed,proof=inputs("U11")
  proof["record"]["q3"]["current_year"]=proof["record"]["nine_months"]["current_year"].copy()
  with self.assertRaises(ValueError):attach(feed,proof)
 def test_prev_period_incorrect_rejected(self):
  feed,proof=inputs("D05");proof["record"]["q3"]["period_start_2025"]="2025-01-01"
  with self.assertRaises(ValueError):attach(feed,proof)
 def test_prior_profit_wrong_rejected(self):
  feed,proof=inputs("O39")
  proof["record"]["nine_months"]["prior_year"]["group_net_profit"]+=1
  with self.assertRaises(ValueError):attach(feed,proof)
 def test_growth_tampered_rejected(self):
  feed,proof=inputs("D05")
  proof["record"]["q3"]["growth_pct"]["net_profit"]=999.9
  with self.assertRaises(ValueError):attach(feed,proof)
 def test_unverified_market_data_rejected(self):
  feed,proof=inputs("U11");feed["records"][0]["price_sgd"]=45.2
  with self.assertRaises(ValueError):attach(feed,proof)

if __name__=="__main__":unittest.main()
