import unittest
from sgx_uob_table_v174 import inspect
class Test(unittest.TestCase):
 def test_reject_fake(self):
  with self.assertRaises(ValueError):inspect(b"%PDF",{"status":"NOT_VERIFIED"})
 def test_reject_wrong_original(self):
  with self.assertRaises(ValueError):inspect(b"%PDF",{"status":"UOB_Q3_CFO_PRIMARY_SGX_PDF_VERIFIED","record":{"symbol":"U11","financial_period_end":"2026-09-30","source_pdf_sha256":"a"*64}})
if __name__=="__main__":unittest.main()
