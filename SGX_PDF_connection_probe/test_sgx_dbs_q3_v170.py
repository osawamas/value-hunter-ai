import unittest
from sgx_dbs_q3_v170 import analyze
class Test(unittest.TestCase):
 def test_original_missing(self):
  with self.assertRaises(ValueError):analyze(b"<html></html>",b"%PDF fake")
 def test_not_pdf(self):
  with self.assertRaises(ValueError):analyze(b"DBS",b"<html>fake</html>")
if __name__=="__main__":unittest.main()
