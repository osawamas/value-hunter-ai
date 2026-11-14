import unittest
from s63_second_site_crosscheck_v129 import compare

def docs():
 f={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
  "ranking_enabled":False,"records":[{"symbol":"S63","price_sgd":9.67,
   "ranking_eligible":False,"quote_source_type":"YAHOO_FINANCE_UNOFFICIAL_CHART",
   "quote_timestamp_utc":"2026-11-13T09:11:27+00:00",
   "quote_url":"https://query1.finance.yahoo.com/v8/finance/chart/S63.SI?interval=1d&range=5d"}]}
 e={"schema_version":"sgx-s63-second-site-price-v128","status":"SECONDARY_EODDATA_S63_HISTORICAL_CLOSE_MATCHED",
  "requested_url":"https://www.eoddata.com/stockquote/SGX/S63.htm",
  "record":{"status":"SECONDARY_EODDATA_S63_HISTORICAL_CLOSE_MATCHED","symbol":"S63",
   "trade_date_sgt":"2026-11-13","currency":"SGD",
   "source_url":"https://www.eoddata.com/stockquote/SGX/S63.htm",
   "close_sgd_research":9.67,"source_html_sha256":"a"*64,
   "different_website_from_yahoo":True,"upstream_market_data_independence_verified":False,
   "original_sgx_exchange_trade_tape_verified":False,"ranking_eligible":False}}
 b={"schema_version":"sgx-s63-buyback-original-v109",
  "status":"SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT",
  "record":{"symbol":"S63","purchase_date":"2026-11-13",
   "issued_excluding_treasury_after_purchase":3115847115,
   "dated_historical_snapshot_only":True,"allow_market_cap_or_per_pbr":False,
   "source_url":"https://links.sgx.com/1.0.0/corporate-announcements/official"}}
 return f,e,b
class Tests(unittest.TestCase):
 def test_two_websites_are_not_verified_trade(self):
  o=compare(*docs())
  self.assertTrue(o["two_website_close_values_match"])
  self.assertFalse(o["upstream_market_data_provider_independence_verified"])
  self.assertFalse(o["ranking_eligible"])
 def test_price_disagreement_is_reported(self):
  f,e,b=docs();e["record"]["close_sgd_research"]=9.73
  self.assertFalse(compare(f,e,b)["two_website_close_values_match"])
 def test_reject_forged_data(self):
  for update in [
   lambda f,e,b:e["record"].update(ranking_eligible=True),
   lambda f,e,b:b["record"].update(issued_excluding_treasury_after_purchase=100),
   lambda f,e,b:f.update(ranking_eligible_count=1),
   lambda f,e,b:f["records"][0].update(quote_source_type="SGX_VERIFIED"),
   lambda f,e,b:e["record"].update(upstream_market_data_independence_verified=True)]:
   f,e,b=docs();update(f,e,b)
   with self.assertRaises(ValueError):compare(f,e,b)
if __name__=="__main__":unittest.main()
