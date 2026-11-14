import unittest
from g13_sgx_buyback_v122 import parse
def sample():
 return ("""<html>Issuer/ Manager GENTING SINGAPORE LIMITED
 Securities GENTING SINGAPORE LIMITED - SGXE21576413 - G13
 Date &amp;Time of Broadcast 10-Jun-2026 17:55:09
 Announcement Reference SG260610OTHRU53S
 Date of Purchase 10/06/2026
 Total Number of shares purchased 2,000,000
 Number of shares cancelled 0
 Number of shares held as treasury shares 2,000,000
 Number of issued shares excluding treasury shares after purchase 12,063,642,274
 Number of treasury shares held after purchase 30,384,550
 </html>""").encode()
class Tests(unittest.TestCase):
 def test_dated_not_current(self):
  x=parse(sample())
  self.assertEqual(x["issued_excluding_treasury_after_purchase"],12063642274)
  self.assertFalse(x["june_30_shares_independently_confirmed"])
  self.assertFalse(x["ranking_eligible"])
 def test_forged_data(self):
  for a,b in [(b"SGXE21576413",b"SG1L01001701"),
              (b"12,063,642,274",b"12,063,600,000"),
              (b"10/06/2026",b"30/06/2026"),
              (b"SG260610OTHRU53S",b"FAKE")]:
   with self.subTest(a=a),self.assertRaises(ValueError):
    parse(sample().replace(a,b))
 def test_duplicate_count(self):
  with self.assertRaises(ValueError):
   parse(sample()+b" Number of treasury shares held after purchase 30,384,550")
if __name__=="__main__":unittest.main()
