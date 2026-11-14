import unittest
from sgx_ocbc_bank_ratios_v149 import parse
class Tests(unittest.TestCase):
 def test_unverified_source_fails(self):
  with self.assertRaises(ValueError):parse(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
 def test_fake_pdf_fails(self):
  m={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED",
   "record":{"records":[{"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":"a"*64}]}}
  p={"status":"OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED",
     "record":{"original_sgx_pdf_sha256":"a"*64}}
  with self.assertRaises(ValueError):parse(b"%PDF counterfeit",m,p)
if __name__=="__main__":unittest.main()
