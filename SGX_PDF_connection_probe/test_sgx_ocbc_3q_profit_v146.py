import unittest
from sgx_ocbc_3q_profit_v146 import parse
class Tests(unittest.TestCase):
 def test_reject_missing_primary_pdf(self):
  with self.assertRaises(ValueError):parse(b"%PDF not really",{"status":"NOT_VERIFIED"})
 def test_reject_hash_mismatch(self):
  d={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED",
     "record":{"schema_version":"sgx-ocbc-q3-pdf-originals-v145",
      "records":[{"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":"a"*64}]}}
  with self.assertRaises(ValueError):parse(b"%PDF fake",d)
if __name__=="__main__":unittest.main()
