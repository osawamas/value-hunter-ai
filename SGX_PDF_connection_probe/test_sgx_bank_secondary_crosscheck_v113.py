import copy
import unittest
from sgx_bank_secondary_crosscheck_v113 import compare

BANKS={"D05":69.90,"O39":28.53,"U11":37.75}

def fixture():
 feed={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
       "ranking_enabled":False,"records":[]}
 market={"schema_version":"sgx-secondary-quote-probe-v112",
         "source_kind":"YAHOO_UNOFFICIAL_DAILY_CHART",
         "promote_to_financial_feed":False,"records":[]}
 for symbol,price in BANKS.items():
  feed["records"].append({"symbol":symbol,"bank_dated_quote_research":{
   "status":"DATED_2026_11_13_THIRD_PARTY_PRICE_RESEARCH_NOT_LIVE",
   "quotation_currency":"SGD","secondary_market_sources_only":True,
   "exchange_official_trade_record_verified":False,
   "current_price_usable_for_valuation":False,
   "historical_trade_date":"2026-11-13","reference_close_sgd":price}})
  url="https://query1.finance.yahoo.com/v8/finance/chart/"+symbol+".SI?interval=1d&range=5d"
  item={"status":"SECONDARY_YAHOO_DAILY_CHART_RESEARCH_ONLY","symbol":symbol,
        "provider_symbol":symbol+".SI","daily_bar_date_sgt":"2026-11-13",
        "close_sgd_research":price+0.000001,"source_url":url,
        "response_sha256":"a"*64,
        "original_sgx_exchange_source_verified":False,
        "actual_exchange_last_trade_timestamp_verified":False,
        "usable_for_market_cap":False,"ranking_eligible":False}
  market["records"].append({"symbol":symbol,"status":item["status"],
                            "source_url":url,"record":item})
 return feed,market

class TestCrosscheck(unittest.TestCase):
 def test_all_three_match_without_elevating(self):
  f,m=fixture();original=copy.deepcopy(f)
  out=compare(f,m)
  self.assertTrue(out["all_three_research_closes_match"])
  self.assertEqual(out["official_sgx_price_verified_count"],0)
  self.assertFalse(out["ranking_eligible"])
  self.assertEqual(original,f)
 def test_conflicting_prices_are_reported_not_hidden(self):
  f,m=fixture()
  m["records"][0]["record"]["close_sgd_research"]=70.14
  x=compare(f,m)
  self.assertFalse(x["all_three_research_closes_match"])
  self.assertFalse(x["records"][0]["two_secondary_research_values_equal_to_cent"])
 def test_date_mismatch_fails_closed(self):
  f,m=fixture();m["records"][1]["record"]["daily_bar_date_sgt"]="2026-11-12"
  with self.assertRaises(ValueError):compare(f,m)
 def test_source_state_mismatch_fails_closed(self):
  f,m=fixture();m["records"][0]["record"]["original_sgx_exchange_source_verified"]=True
  with self.assertRaises(ValueError):compare(f,m)
 def test_missing_symbol_fails(self):
  f,m=fixture();m["records"].pop()
  with self.assertRaises(ValueError):compare(f,m)
if __name__=="__main__":unittest.main()
