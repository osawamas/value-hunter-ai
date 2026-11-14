import unittest
from sgx_ocbc_text_context_v151 import extract
class Tests(unittest.TestCase):
 def test_reject_unverified_manifest(self):
  with self.assertRaises(ValueError):extract(b"%PDF",{"status":"NOT_VERIFIED"})
 def test_reject_wrong_pdf_hash(self):
  m={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED",
    "record":{"symbol":"O39","records":[{"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":"a"*64}]}}
  with self.assertRaises(ValueError):extract(b"%PDF-not-original",m)
if __name__=="__main__":unittest.main()
