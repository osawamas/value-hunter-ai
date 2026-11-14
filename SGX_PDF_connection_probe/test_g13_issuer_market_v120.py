import unittest
from g13_issuer_market_v120 import extract

def sample():
 return ("""<html><body>Quotes Delayed 10 Minutes
 SGX Symbol: G13 Currency: SGD
 Last Done: 0.575 Volume ('000): 88,233.4
 Updated: 13 Nov 2026 17:16
 Issued &amp; Paid-up Shares 3 12,063,642,274
 3. Updated on 14/08/2026 and rounded to the nearest thousand.
 </body></html>""").encode()

class Tests(unittest.TestCase):
 def test_historical_not_authorized(self):
  a=extract(sample())
  self.assertEqual(a["research_last_done_sgd"],0.575)
  self.assertEqual(a["ir_shares_count"],12063642274)
  self.assertFalse(a["market_cap_per_pbr_permitted"])
  self.assertFalse(a["source_is_sgx_trade_tape"])
 def test_tamper(self):
  for old,new in ((b"SGX Symbol: G13",b"SGX Symbol: U11"),
                  (b"Currency: SGD",b"Currency: USD"),
                  (b"0.575",b"0.5755"),
                  (b"14/08/2026",b"13/11/2026"),
                  (b"Quotes Delayed 10 Minutes",b"Live trades")):
   with self.subTest(old=old),self.assertRaises(ValueError):
    extract(sample().replace(old,new))
if __name__=="__main__":unittest.main()
