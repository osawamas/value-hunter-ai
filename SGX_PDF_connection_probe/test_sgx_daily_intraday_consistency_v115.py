import unittest
from sgx_daily_intraday_consistency_v115 import compare

def data():
 daily={"schema_version":"sgx-secondary-quote-probe-v112",
        "source_kind":"YAHOO_UNOFFICIAL_DAILY_CHART",
        "promote_to_financial_feed":False,"records":[]}
 bars={"schema_version":"sgx-secondary-intraday-v114",
       "research_provider":"YAHOO_FINANCE_UNOFFICIAL",
       "promoted_to_financial_feed":False,"records":[]}
 for s,p in (("D05",69.9),("O39",28.53),("U11",37.75)):
  a={"status":"SECONDARY_YAHOO_DAILY_CHART_RESEARCH_ONLY",
     "symbol":s,"provider_symbol":s+".SI","daily_bar_date_sgt":"2026-11-13",
     "close_sgd_research":p,"actual_exchange_last_trade_timestamp_verified":False,
     "ranking_eligible":False}
  b={"status":"YAHOO_SGX_INTRADAY_BAR_RESEARCH_ONLY",
     "symbol":s,"provider_symbol":s+".SI","last_bar_date_sgt":"2026-11-13",
     "last_bar_price_sgd":p+0.000001,"bar_timestamp_is_verified_trade_time":False,
     "price_independently_exchange_confirmed":False,"ranking_eligible":False}
  daily["records"].append({"symbol":s,"record":a})
  bars["records"].append({"symbol":s,"record":b})
 return daily,bars

class Tests(unittest.TestCase):
 def test_price_matches_do_not_verify_sgx(self):
  x,y=data();z=compare(x,y)
  self.assertEqual(z["matching_price_count"],3)
  self.assertEqual(z["official_exchange_confirmed_quotes"],0)
  self.assertFalse(z["ranking_eligible"])
 def test_price_disagreement_is_reported(self):
  x,y=data();y["records"][0]["record"]["last_bar_price_sgd"]=70.14
  self.assertEqual(compare(x,y)["matching_price_count"],2)
 def test_different_day_fails(self):
  x,y=data();y["records"][0]["record"]["last_bar_date_sgt"]="2026-11-12"
  with self.assertRaises(ValueError):compare(x,y)
 def test_fake_verified_fails(self):
  x,y=data();y["records"][0]["record"]["bar_timestamp_is_verified_trade_time"]=True
  with self.assertRaises(ValueError):compare(x,y)
 def test_missing_fails(self):
  x,y=data();x["records"].pop()
  with self.assertRaises(ValueError):compare(x,y)
if __name__=="__main__":unittest.main()
