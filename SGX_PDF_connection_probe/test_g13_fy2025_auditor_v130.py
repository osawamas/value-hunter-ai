"""v130 structural safety controls; live PDF interpretation is tested in CI."""
import unittest
from g13_fy2025_auditor_v130 import parse
class Tests(unittest.TestCase):
 def test_missing_pdf_fails(self):
  with self.assertRaises(ValueError):
   parse(b"<html>not annual PDF</html>",{"schema_version":"value_hunter_web_v29",
            "ranking_eligible_count":0,"records":[]})
 def test_wrong_ranking_state_fails(self):
  with self.assertRaises(ValueError):
   parse(b"%PDF-"+b"x"*100,{"schema_version":"value_hunter_web_v29",
            "ranking_eligible_count":1,"records":[]})
 def test_missing_source_fails(self):
  with self.assertRaises(ValueError):
   parse(b"%PDF-"+b"x"*100,{"schema_version":"value_hunter_web_v29",
            "ranking_eligible_count":0,"records":[]})
if __name__=="__main__":unittest.main()
