import unittest
from sgx_dbs_exact_table_v180 import find_unique,analyze
class Tests(unittest.TestCase):
 def test_original_table_column_sequence(self):
  a=["Of which: Net interest income","3,711","3,578","4","3,581","4","10,786","10,542","2"]
  self.assertEqual(find_unique(a,"Of which: Net interest income",a[1:])["source_column_values"][0],"3,711")
 def test_changed_column_rejected(self):
  with self.assertRaises(ValueError):find_unique(["Net profit","2,954","2,813"],"Net profit",["2,813","2,954"])
 def test_duplicated_row_rejected(self):
  with self.assertRaises(ValueError):find_unique(["Net profit","2,813","Net profit","2,813"],"Net profit",["2,813"])
 def test_unverified_original_rejected(self):
  with self.assertRaises(ValueError):analyze(b"%PDF",{"status":"NOT_VERIFIED"},{"status":"NOT_VERIFIED"})
if __name__=="__main__":unittest.main()
