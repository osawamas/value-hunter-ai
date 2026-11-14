import unittest
from sgx_s63_buyback_v109 import parse
def sample():
 return ("""<html><body>Issuer/ Manager SINGAPORE TECHNOLOGIES ENGINEERING LTD
 Securities SINGAPORE TECH ENGINEERING LTD - SG1F60858221 - S63
 Date &amp;Time of Broadcast 13-Nov-2026 18:21:18
 Announcement Reference SG261113OTHRPXGV
 Date of Purchase | 13/11/2026 |
 Total Number of shares purchased | 500,000 |
 Number of shares cancelled | 0 |
 Number of shares held as treasury shares | 500,000 |
 Number of issued shares excluding treasury shares after purchase 3,115,847,115
 Number of treasury shares held after purchase 6,648,082
 </body></html>""").encode()
class Tests(unittest.TestCase):
 def test_historical_source_not_valuation(self):
  x=parse(sample())
  self.assertEqual(x["shares_purchased"],500000)
  self.assertEqual(x["issued_excluding_treasury_after_purchase"],3115847115)
  self.assertFalse(x["allow_market_cap_or_per_pbr"])
  self.assertFalse(x["ranking_eligible"])
 def test_adversarial_mutations(self):
  for old,new in ((b"SG261113OTHRPXGV",b"SG261113FAKE"),
                  (b"SG1F60858221",b"SG1FAKE00000"),
                  (b"500,000",b"400,000"),
                  (b"3,115,847,115",b"3,115,000,000"),
                  (b"13-Nov-2026 18:21:18",b"14-Nov-2026 18:21:18")):
   with self.subTest(old=old),self.assertRaises(ValueError):
    parse(sample().replace(old,new))
 def test_duplicate_historical_value_rejected(self):
  with self.assertRaises(ValueError):
   parse(sample()+b" Number of treasury shares held after purchase 6,648,082")
if __name__=="__main__":unittest.main()
