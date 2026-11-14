import unittest
from sgx_ocbc_q3_two_pdf_v148 import compare
class Tests(unittest.TestCase):
 def test_prior_source_must_be_trusted(self):
  with self.assertRaises(ValueError):compare({"status":"NOT_VERIFIED"}, {},b"%PDF")
 def test_reject_fake_pdf(self):
  a={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED",
    "record":{"schema_version":"sgx-ocbc-q3-pdf-originals-v145","records":[
     {"filename":"OCBC_3Q26_Results_Highlights.pdf","sha256":"a"*64}]}}
  b={"status":"OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED",
    "record":{"schema_version":"sgx-ocbc-3q26-official-bank-results-v146"}}
  with self.assertRaises(ValueError):compare(a,b,b"%PDF-fake")
if __name__=="__main__":unittest.main()
