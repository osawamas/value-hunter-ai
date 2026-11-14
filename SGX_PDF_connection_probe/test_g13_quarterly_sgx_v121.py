import unittest
from g13_quarterly_sgx_v121 import parse_text

def fixture():
 return """Genting Singapore Limited QUARTERLY BUSINESS OVERVIEW
 in respect of the three months ended 30 September 2026
 Total Revenue     566,096   649,790   (13)  595,951  (5)
 Net profit after taxation    54,731   94,618   (42) 90,884 (40)
 Financial information presented in this quarterly business overview was prepared
 based on the management accounts of the Group and the same has not been audited nor reviewed
 by the Company's auditors.
"""
class Tests(unittest.TestCase):
 def test_unreviewed_decline_cannot_be_repriced(self):
  r=parse_text(fixture(),"a"*64)
  self.assertLess(r["revenue_yoy_pct"],-12)
  self.assertLess(r["net_profit_yoy_pct"],-40)
  self.assertFalse(r["financials_audited"])
  self.assertFalse(r["ranking_eligible"])
 def test_bad_numbers(self):
  with self.assertRaises(ValueError):
   parse_text(fixture().replace("566,096","666,096"),"a"*64)
 def test_wrong_period(self):
  with self.assertRaises(ValueError):
   parse_text(fixture().replace("30 September 2026","30 June 2026"),"a"*64)
 def test_no_audit_disclaimer(self):
  with self.assertRaises(ValueError):
   parse_text(fixture().replace("not been audited nor reviewed","was audited and reviewed"),"a"*64)
if __name__=="__main__":unittest.main()
