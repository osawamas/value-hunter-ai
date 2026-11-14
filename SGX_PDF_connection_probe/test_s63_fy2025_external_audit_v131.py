import unittest
from s63_fy2025_external_audit_v131 import parse
def feed():
 return {"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
  "records":[{"symbol":"S63","ranking_eligible":False,"fiscal_year":2025,
              "revenue_sgd_thousands":12346426}]}
class Tests(unittest.TestCase):
 def test_bad_pdf_rejected(self):
  with self.assertRaises(ValueError):parse(b"<html>fake report</html>",feed())
 def test_bad_feed_rejected(self):
  f=feed();f["ranking_eligible_count"]=1
  with self.assertRaises(ValueError):parse(b"%PDF-"+b"x"*100,f)
 def test_bad_symbol_rejected(self):
  f=feed();f["records"][0]["symbol"]="G13"
  with self.assertRaises(ValueError):parse(b"%PDF-"+b"x"*100,f)
if __name__=="__main__":unittest.main()
