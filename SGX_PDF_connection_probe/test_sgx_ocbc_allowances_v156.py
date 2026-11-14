import unittest
from sgx_ocbc_allowances_v156 import extract
class Tests(unittest.TestCase):
 def test_untrusted_source(self):
  with self.assertRaises(ValueError):extract(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
 def test_hash_mismatch(self):
  manifest={"status":"SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED",
   "record":{"records":[{"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":"a"*64}]}}
  components={"status":"OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED",
   "record":{"original_pdf_sha256":"a"*64,"bank_statements":{"9M26":{"allowances_charged":424}},"ranking_eligible":False}}
  with self.assertRaises(ValueError):extract(b"%PDF-fake",manifest,components)
if __name__=="__main__":unittest.main()
