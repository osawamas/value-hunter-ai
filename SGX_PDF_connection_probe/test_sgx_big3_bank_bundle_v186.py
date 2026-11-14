import unittest
from sgx_big3_bank_bundle_v186 import normalize
class Tests(unittest.TestCase):
 def test_incomplete_original(self):
  with self.assertRaises(ValueError):normalize({}, {}, {}, {})
 def test_no_invented_comparability(self):
  with self.assertRaises(ValueError):normalize({"status":"NOT_VERIFIED"}, {}, {}, {})
if __name__=="__main__":unittest.main()
