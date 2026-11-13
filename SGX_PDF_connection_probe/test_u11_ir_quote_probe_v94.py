"""v94: reject IR quote snapshots without exact timestamp and content origin."""
import unittest
from u11_ir_quote_probe_v94 import parse,URL

def source(*,price="37.750",timestamp="13 Nov 2026 17:14",extra=""):
 return ('<html><title>UOB quotes</title><p>UOB stock quote</p>'
   '<script>var feed={"quotes":{"last_done":"'+price+
   '","datetime":"'+timestamp+'"}};</script>'+extra+'</html>').encode()

class Tests(unittest.TestCase):
 def test_historical_issuer_ir_snapshot_not_valuation(self):
  r=parse(URL,source())
  self.assertEqual(r["price_sgd_reference"],37.75)
  self.assertEqual(r["quote_as_of_local"],"2026-11-13T17:14+08:00")
  self.assertFalse(r["eligible_for_live_market_cap"])
  self.assertFalse(r["eligible_for_per_pbr"])
  self.assertFalse(r["ranking_eligible"])
  self.assertFalse(r["exchange_trade_tick_independently_verified"])
 def test_page_has_no_quote_fails_closed(self):
  with self.assertRaises(ValueError):parse(URL,b"<html><title>Just a landing page</title></html>")
 def test_different_issuer_origin_rejected(self):
  with self.assertRaises(ValueError):parse("https://evil.example/",source())
 def test_timestamp_does_not_match_date(self):
  with self.assertRaises(ValueError):parse(URL,source(timestamp="12 Nov 2026 17:14"))
 def test_tampered_price_refused(self):
  with self.assertRaises(ValueError):parse(URL,source(price="55.150"))
 def test_price_ambiguous_rejected(self):
  x=source(extra='<script>{"last_done":"35.500"}</script>')
  with self.assertRaises(ValueError):parse(URL,x)

if __name__=="__main__":unittest.main()
