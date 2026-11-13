"""v95: historical bank research quotes stay out of market pricing/ranking."""
import unittest
from bank_quote_research_v95 import EVIDENCE,STATUS,attach

def feed():
 records=[]
 for sym in ("D05","O39","U11"):
  records.append({"symbol":sym,"ranking_eligible":False,
   "bank_market_readiness":{"status":"NOT_READY_PRIMARY_SHARES_AND_TIMED_QUOTES_MISSING"},
   "shares_outstanding":None,"price_sgd":None,"market_cap_sgd":None,
   "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None})
 records.append({"symbol":"S68","price_sgd":None,"ranking_eligible":False})
 return {"schema_version":"value_hunter_web_v29","records":records}

class Tests(unittest.TestCase):
 def test_all_three_bank_research_prices_are_historical_only(self):
  src=feed();out=attach(src)
  for rec in out["records"][:3]:
   researched=rec["bank_dated_quote_research"]
   self.assertEqual(researched["status"],STATUS)
   self.assertEqual(researched["historical_trade_date"],"2026-11-13")
   self.assertEqual(researched["reference_close_sgd"],float(EVIDENCE[rec["symbol"]]["price"]))
   self.assertTrue(researched["static_observation_not_automated_live_fetch"])
   self.assertFalse(researched["current_price_usable_for_valuation"])
   self.assertFalse(researched["exchange_official_trade_record_verified"])
   self.assertIsNone(rec["price_sgd"])
   self.assertIsNone(rec["per_reference"])
   self.assertFalse(rec["ranking_eligible"])
  self.assertEqual(out["records"][-1],src["records"][-1])
  self.assertNotIn("bank_dated_quote_research",src["records"][0])
 def test_dbs_disagreement_is_not_silently_hidden(self):
  out=attach(feed())
  mismatch=out["records"][0]["bank_dated_quote_research"]["price_source_disagreement"]
  self.assertEqual(mismatch["displayed"],"70.14")
  self.assertIn("NOT_ADOPTED",mismatch["reason"])
 def test_current_quote_injection_rejected(self):
  f=feed();f["records"][1]["price_sgd"]=28.53
  with self.assertRaises(ValueError):attach(f)
 def test_missing_provenance_rejected(self):
  f=feed();f["records"][2].pop("bank_market_readiness")
  with self.assertRaises(ValueError):attach(f)
 def test_duplicate_bank_rejected(self):
  f=feed();f["records"].append(f["records"][0].copy())
  with self.assertRaises(ValueError):attach(f)
 def test_wrong_currency_source_values_rejected(self):
  e=EVIDENCE["D05"]["observations"][0]
  old=e["observed"]
  try:
   e["observed"]="70.14"
   with self.assertRaises(ValueError):attach(feed())
  finally:e["observed"]=old

if __name__=="__main__":unittest.main()
