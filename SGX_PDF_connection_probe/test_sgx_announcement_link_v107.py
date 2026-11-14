import unittest
from sgx_announcement_link_v107 import parse
def fixture(counter="D05",isin="SG1L01001701",ref="SG260309OTHROF8R"):
 return (f"<html><body><h2>Issuer &amp; Securities</h2><p>Issuer/ Manager DBS GROUP HOLDINGS LTD</p>"
         f"<p>Securities DBS GROUP HOLDINGS LTD - {isin} - {counter}</p>"
         f"<p>Date &amp;Time of Broadcast 09-Mar-2026 07:33:28</p>"
         f"<p>Announcement Reference {ref}</p></body></html>").encode()
class AnnouncementTests(unittest.TestCase):
 def test_primary_pair_is_historical_only(self):
  x=parse(fixture())
  self.assertEqual(x["symbol"],"D05")
  self.assertFalse(x["issuer_active_as_of_now_verified"])
  self.assertFalse(x["official_entire_sgx_master_verified"])
  self.assertFalse(x["ranking_eligible"])
 def test_conflicts_refused(self):
  for b in (fixture(counter="U11"),fixture(isin="SG1M31001969"),
            fixture(ref="SG261113OTHRHOAF"),fixture()+b" Securities DBS GROUP HOLDINGS LTD - SG1L01001701 - D05"):
   with self.subTest(b=b[-40:]),self.assertRaises(ValueError):parse(b)
if __name__=="__main__":unittest.main()
