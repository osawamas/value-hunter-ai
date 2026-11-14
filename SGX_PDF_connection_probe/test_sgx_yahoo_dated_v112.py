"""v112 market data test: no dated secondary prices enter verified valuations."""
import json
import unittest
from datetime import datetime,timezone,timedelta
from sgx_yahoo_dated_v112 import parse, SOURCES

NOW=datetime(2026,11,14,4,0,tzinfo=timezone.utc)
def payload(symbol="D05",clock=NOW-timedelta(hours=12),price=69.90):
    return json.dumps({"chart":{"error":None,"result":[{
        "meta":{"symbol":SOURCES[symbol],"currency":"SGD",
                "exchangeTimezoneName":"Asia/Singapore","instrumentType":"EQUITY"},
        "timestamp":[int(clock.timestamp())],
        "indicators":{"quote":[{"close":[price]}]}
    }]}}).encode()

class ChartTests(unittest.TestCase):
    def test_research_only_all_banks(self):
        for symbol in SOURCES:
            with self.subTest(symbol=symbol):
                r=parse(symbol,payload(symbol),NOW)
                self.assertFalse(r["original_sgx_exchange_source_verified"])
                self.assertFalse(r["independent_price_crosscheck_completed"])
                self.assertFalse(r["usable_for_market_cap"])
                self.assertFalse(r["usable_for_per_pbr"])
                self.assertFalse(r["ranking_eligible"])
    def test_wrong_counter_currency_or_type(self):
        d=json.loads(payload())
        for key,value in (("symbol","U11.SI"),("currency","USD"),
                          ("exchangeTimezoneName","America/New_York"),
                          ("instrumentType","INDEX")):
            obj=json.loads(payload());obj["chart"]["result"][0]["meta"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                parse("D05",json.dumps(obj).encode(),NOW)
    def test_stale_future_invalid_price(self):
        for clock,price in ((NOW-timedelta(days=11),10),
                            (NOW+timedelta(hours=1),10),
                            (NOW-timedelta(hours=12),float("nan")),
                            (NOW-timedelta(hours=12),-5)):
            with self.subTest(clock=clock,price=price),self.assertRaises(ValueError):
                parse("D05",payload(clock=clock,price=price),NOW)
    def test_duplicate_bar_and_missing_bars(self):
        d=json.loads(payload())
        o=d["chart"]["result"][0]
        o["timestamp"]*=2;o["indicators"]["quote"][0]["close"]*=2
        with self.assertRaises(ValueError):parse("D05",json.dumps(d).encode(),NOW)
        o["timestamp"]=[o["timestamp"][0]]
        o["indicators"]["quote"][0]["close"]=[]
        with self.assertRaises(ValueError):parse("D05",json.dumps(d).encode(),NOW)
if __name__=="__main__":unittest.main()
