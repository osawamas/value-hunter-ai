import unittest
from sgx_ocbc_bank_components_v154 import find_table_amount,extract
class Tests(unittest.TestCase):
 def test_unique_row(self):
  rows=["Net interest income","2,313","Non-interest income","1,420"]
  x=find_table_amount(rows,"Net interest income",2313)
  self.assertEqual(x["value_sgd_millions"],2313)
 def test_negative_allowance_row(self):
  x=find_table_amount(["Allowances","(52)"],"Allowances",52)
  self.assertTrue(x["negative_expense_presentation"])
 def test_ambiguous_source(self):
  with self.assertRaises(ValueError):find_table_amount(["Allowances","(52)","Allowances","(52)"],"Allowances",52)
 def test_amount_tamper_rejected(self):
  with self.assertRaises(ValueError):find_table_amount(["Net interest income","2,131"],"Net interest income",2313)
 def test_not_primary_pdf(self):
  with self.assertRaises(ValueError):extract(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
if __name__=="__main__":unittest.main()
