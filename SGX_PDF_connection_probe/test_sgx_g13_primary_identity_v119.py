import unittest
from sgx_g13_primary_identity_v119 import parse

def fixture():
 return ("""<html><body>Issuer/ Manager GENTING SINGAPORE LIMITED
 Securities GENTING SINGAPORE LIMITED - SGXE21576413 - G13
 Date &amp;Time of Broadcast 30-Jan-2026 17:20:38
 Announcement Reference SG260130OTHRZ1XN</body></html>""").encode()

class Tests(unittest.TestCase):
 def test_historical_proof_not_eligibility(self):
  r=parse(fixture())
  self.assertEqual(r["symbol"],"G13")
  self.assertEqual(r["isin"],"SGXE21576413")
  self.assertFalse(r["current_shares_verified"])
  self.assertFalse(r["market_cap_per_pbr_use_permitted"])
  self.assertFalse(r["ranking_eligible"])
 def test_tamper_cases(self):
  for a,b in [(b"SGXE21576413",b"SG1L01001701"),(b"G13",b"S68"),
              (b"SG260130OTHRZ1XN",b"SG260130FAKE"),
              (b"30-Jan-2026 17:20:38",b"30-Jan-2026 18:20:38")]:
   with self.subTest(b=b),self.assertRaises(ValueError):
    parse(fixture().replace(a,b))
 def test_duplicate_identity_fails(self):
  with self.assertRaises(ValueError):
   parse(fixture()+b" GENTING SINGAPORE LIMITED - SGXE21576413 - G13")
if __name__=="__main__":
 unittest.main()
