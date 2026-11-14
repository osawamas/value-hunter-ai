import unittest
from sgx_ocbc_balance_rows_v158 import analyze
class Tests(unittest.TestCase):
 def test_fake_source_rejected(self):
  with self.assertRaises(ValueError):analyze(b"%PDF-fake",{"status":"NOT_VERIFIED"})
 def test_bad_digest_rejected(self):
  m={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED","record":{"records":[
   {"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":"a"*64}]}}
  with self.assertRaises(ValueError):analyze(b"%PDF-fake",m)
if __name__=="__main__":unittest.main()
