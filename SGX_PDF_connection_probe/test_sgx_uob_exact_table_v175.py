import unittest
from sgx_uob_exact_table_v175 import row,analyze
class Tests(unittest.TestCase):
 def test_3q_and_9m_position(self):
  a=["Net profit","4,165","3,271","27","1,250","1,478","(15)","443",">100"]
  d=row(a,"Net profit",(4165,3271,1250,443))
  self.assertEqual(d["3q26"],1250)
  self.assertEqual(d["9m26"],4165)
 def test_shifted_column_rejected(self):
  with self.assertRaises(ValueError):row(["Net profit","1,250","3,271","27","4,165","1,478","(15)","443",">100"],"Net profit",(4165,3271,1250,443))
 def test_fake_source_rejected(self):
  with self.assertRaises(ValueError):analyze(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
if __name__=="__main__":unittest.main()
