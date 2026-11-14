import unittest
from sgx_dbs_table_locator_v179 import inspect
class Tests(unittest.TestCase):
 def test_missing_prior_source_rejected(self):
  with self.assertRaises(ValueError):inspect(b"%PDF",{"status":"NOT_VERIFIED"})
 def test_wrong_content_hash_rejected(self):
  p={"status":"SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED",
     "record":{"dbs_official_trading_pdf_sha256":"a"*64,
               "dbs_trading_pdf_single_table_row_column_reperformance_completed":False}}
  with self.assertRaises(ValueError):inspect(b"%PDF fake",p)
if __name__=="__main__":unittest.main()
