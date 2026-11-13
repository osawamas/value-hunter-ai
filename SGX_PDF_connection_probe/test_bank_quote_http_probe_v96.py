"""v96 secondary quote HTML is diagnostic; refuses missing ticker/date/multiple blocks."""
import unittest
from bank_quote_http_probe_v96 import parse,SOURCES,STATUS

def html(symbol,*,price="37.750",day="2026-11-13",time="17:16",duplicate=False,wrong_isin=False):
 s=SOURCES[symbol]
 part=('SGX:'+symbol+' '+s["identity"]+' ISIN Code '+
       ("SG1FAKE" if wrong_isin else s["isin"])+
       ' SGD '+price+' -0.020 / -0.05% Share Price as of: '+
       day+' '+time)
 if duplicate:part+=' '+part
 return ('<html><head><title>SGX stock info</title></head><body><p>'+
         part+'</p></body></html>').encode()

class QuoteTests(unittest.TestCase):
 def test_all_three_typed_research_quotes(self):
  for symbol,price in (("D05","69.900"),("O39","28.530"),("U11","37.750")):
   record=parse(symbol,html(symbol,price=price))
   self.assertEqual(record["symbol"],symbol)
   self.assertEqual(record["status"],STATUS)
   self.assertEqual(record["quote_price_sgd"],float(price))
   self.assertEqual(record["quote_timezone"],"Asia/Singapore")
   self.assertFalse(record["usable_for_current_market_cap"])
   self.assertFalse(record["usable_for_per_pbr"])
   self.assertFalse(record["ranking_eligible"])
 def test_wrong_isin_rejected(self):
  with self.assertRaises(ValueError):parse("U11",html("U11",wrong_isin=True))
 def test_future_date_rejected(self):
  with self.assertRaises(ValueError):parse("U11",html("U11",day="2026-11-15"))
 def test_malformed_timestamp_rejected(self):
  with self.assertRaises(ValueError):parse("U11",html("U11",time="bad"))
 def test_multiple_header_prices_rejected(self):
  with self.assertRaises(ValueError):parse("U11",html("U11",duplicate=True))
 def test_wrong_ticker_rejected(self):
  with self.assertRaises(ValueError):parse("D05",html("U11"))
 def test_unusable_site_response_rejected(self):
  with self.assertRaises(ValueError):parse("O39",b"<html>Access denied 403</html>")
if __name__=="__main__":unittest.main()
