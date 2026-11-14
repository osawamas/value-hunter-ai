import unittest
from sgx_ocbc_bank_balance_v159 import read_row,extract
class Tests(unittest.TestCase):
 def test_exact_ord_equity(self):
  self.assertEqual(read_row(["Ordinary equity","60,899","58,263"],"Ordinary equity",60899)["sgd_millions"],60899)
 def test_disallow_alternate_value(self):
  with self.assertRaises(ValueError):read_row(["Ordinary equity","63,347"],"Ordinary equity",60899)
 def test_duplicate_label(self):
  with self.assertRaises(ValueError):read_row(["Total assets","731,689","Total assets","731,689"],"Total assets",731689)
 def test_unverified_pdf(self):
  with self.assertRaises(ValueError):extract(b"%PDF",{"status":"NOT_VERIFIED"})
if __name__=="__main__":unittest.main()
