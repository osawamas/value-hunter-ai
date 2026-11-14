import json
import unittest
from datetime import datetime,timedelta,timezone
from sgx_intraday_v114 import parse,TICKERS
NOW=datetime(2026,11,14,4,tzinfo=timezone.utc)
TIME=datetime(2026,11,13,8,tzinfo=timezone.utc)

def fixture(symbol="D05",price=69.9):
 return {"chart":{"error":None,"result":[{
   "meta":{"symbol":TICKERS[symbol],"currency":"SGD",
           "exchangeTimezoneName":"Asia/Singapore","instrumentType":"EQUITY"},
   "timestamp":[int(TIME.timestamp())],
   "indicators":{"quote":[{"close":[price]}]}
 }]}}

def raw(x):return json.dumps(x).encode()

class Tests(unittest.TestCase):
 def test_historical_bar_not_a_verified_trade(self):
  for symbol in TICKERS:
   r=parse(symbol,raw(fixture(symbol)),NOW)
   self.assertEqual(r["last_bar_date_sgt"],"2026-11-13")
   self.assertFalse(r["bar_timestamp_is_verified_trade_time"])
   self.assertFalse(r["eligible_for_market_cap_per_pbr"])
   self.assertFalse(r["ranking_eligible"])
 def test_incorrect_market(self):
  for field,value in (("symbol","U11.SI"),("currency","USD"),
                      ("exchangeTimezoneName","America/New_York"),
                      ("instrumentType","INDEX")):
   x=fixture();x["chart"]["result"][0]["meta"][field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):
    parse("D05",raw(x),NOW)
 def test_duplicate_and_stale(self):
  x=fixture();d=x["chart"]["result"][0]
  d["timestamp"]*=2;d["indicators"]["quote"][0]["close"]*=2
  with self.assertRaises(ValueError):parse("D05",raw(x),NOW)
  x=fixture();d=x["chart"]["result"][0]
  d["timestamp"]=[int((TIME-timedelta(days=10)).timestamp())]
  with self.assertRaises(ValueError):parse("D05",raw(x),NOW)
 def test_no_acceptable_bars(self):
  x=fixture();d=x["chart"]["result"][0]
  d["timestamp"]=[int(datetime(2026,11,14,4,tzinfo=timezone.utc).timestamp())]
  with self.assertRaises(ValueError):parse("D05",raw(x),NOW)
 def test_future_bar_and_invalid_price(self):
  x=fixture();d=x["chart"]["result"][0]
  d["timestamp"]=[int((NOW+timedelta(days=2)).timestamp())]
  with self.assertRaises(ValueError):parse("D05",raw(x),NOW)
  x=fixture();x["chart"]["result"][0]["indicators"]["quote"][0]["close"]=[-1]
  with self.assertRaises(ValueError):parse("D05",raw(x),NOW)
if __name__=="__main__":unittest.main()
