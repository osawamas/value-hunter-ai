import unittest
from sgx_big3_nii_v177 import combine
class Tests(unittest.TestCase):
 def test_fake_pdf_rejected(self):
  with self.assertRaises(ValueError):combine(b"<html>fake</html>",{},{},{})
 def test_mismatched_sources_rejected(self):
  with self.assertRaises(ValueError):combine(b"%PDF invalid",{"status":"NOT_VERIFIED"},{},{})
if __name__=="__main__":unittest.main()
