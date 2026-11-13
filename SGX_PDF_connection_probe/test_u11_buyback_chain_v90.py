"""v90: three original SGX buyback notices must reconcile day by day."""
import unittest
from u11_buyback_chain_v90 import verify,NOTICES

def html(day,ref,net,treasury):
 d,m,y=day[8:10],day[5:7],day[:4]
 return ("<html><body><h1>Share Buy Back - Daily Share Buy-Back Notice</h1>"
         "<p>UNITED OVERSEAS BANK LIMITED</p>"
         "<p>Announcement Reference</p><p>"+ref+"</p>"
         "<p>Daily Share Buy-Back Notice</p>"
         "<h2>Section A</h2><p>Date of Purchase</p><p>"+d+"/"+m+"/"+y+"</p>"
         "<h2>Section D</h2>"
         "<p>Number of issued shares excluding treasury shares after purchase</p><p>"+f"{net:,}"+"</p>"
         "<p>Number of treasury shares held after purchase</p><p>"+f"{treasury:,}"+"</p>"
         "</body></html>").encode()

def load(*,bad_second=False,bad_date=False):
 data={}
 for i,(day,ref,url,net,treasury) in enumerate(NOTICES):
  if bad_second and i==1:net+=100
  if bad_date and i==2:day="2026-11-11"
  data[url]=html(day,ref,net,treasury)
 return lambda url:data[url]

class ChainTests(unittest.TestCase):
 def test_three_dates_and_daily_stock_changes(self):
  proof=verify(load())
  self.assertEqual(len(proof["records"]),3)
  self.assertEqual(proof["consecutive_day_net_decrease"],34000)
  self.assertEqual(proof["records"][-1]["issued_excluding_treasury"],1646711591)
  self.assertFalse(proof["later_2026_11_13_claim_verified"])
  self.assertFalse(proof["current_market_cap_eligible"])
  self.assertFalse(proof["ranking_eligible"])
 def test_changed_bank_share_count_rejected(self):
  with self.assertRaises(ValueError):verify(load(bad_second=True))
 def test_wrong_issuer_purchase_date_rejected(self):
  with self.assertRaises(ValueError):verify(load(bad_date=True))
 def test_missing_primary_filing_fails_closed(self):
  with self.assertRaises(ValueError):verify(lambda _:b"HTTP 403 blocked")
if __name__=="__main__":unittest.main()
