import unittest
from sgx_ocbc_exact_profit_v152 import parse_text_lines,extract
class Tests(unittest.TestCase):
 def test_exact_table_rows(self):
  rows=["Some header","Group net profit","2,042","1,978","other"]
  x=parse_text_lines(rows,"3Q26","2,042","1,978")
  self.assertEqual(x["current_sgd_millions"],2042)
 def test_wrong_period_or_columns(self):
  rows=["Group net profit","1,978","2,042"]
  with self.assertRaises(ValueError):parse_text_lines(rows,"3Q26","2,042","1,978")
 def test_duplicate_label(self):
  with self.assertRaises(ValueError):parse_text_lines(["Group net profit","2,042","1,978","Group net profit"],"3Q26","2,042","1,978")
 def test_untrusted_manifest(self):
  with self.assertRaises(ValueError):extract(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
if __name__=="__main__":unittest.main()
