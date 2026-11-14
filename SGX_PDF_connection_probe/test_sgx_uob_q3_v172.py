import unittest
from sgx_uob_q3_v172 import analyze
class Tests(unittest.TestCase):
 def test_no_fake_document(self):
  with self.assertRaises(ValueError):analyze(b"<html>fake</html>")
 def test_unreadable_pdf(self):
  with self.assertRaises(Exception):analyze(b"%PDF-invalid")
if __name__=="__main__":unittest.main()
