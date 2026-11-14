import unittest
from sgx_securities_prices_probe_v134 import inspect

def sample():
 return b"""<html><body><h1>Securities Prices</h1><p>Trading Name Trading Code Download
 ST Engineering S63 Mainboard Genting Sing G13 Mainboard DBS D05 Mainboard
 </p></body></html>"""
class Tests(unittest.TestCase):
 def test_html_ticker_presence_not_listing_verification(self):
  x=inspect(sample())
  self.assertTrue(x["page_contains_multi_ticker_visible_table_evidence"])
  self.assertFalse(x["complete_official_sgx_security_master_retrieved"])
  self.assertFalse(x["eligible_for_ranking"])
 def test_js_skeleton_still_not_full_master(self):
  x=inspect(b"<html>Loading securities...</html>"*8)
  self.assertFalse(x["page_contains_multi_ticker_visible_table_evidence"])
  self.assertTrue(x["js_rendering_or_access_failure_possible"])
 def test_non_html_fails(self):
  with self.assertRaises(ValueError):inspect(sample(),"application/pdf")
if __name__=="__main__":unittest.main()
