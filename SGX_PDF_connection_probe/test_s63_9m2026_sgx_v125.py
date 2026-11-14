import unittest
from s63_9m2026_sgx_v125 import parse

def t():
 return """ST Engineering 9M2026 Market Update
 13 November 2026
 Strong 9M Revenue Growth of 10% y-o-y
 3Q2026 9M2026 Revenue $10.0b
 $13.2b Contract Wins
 Order Book $37.7b
 """
class Tests(unittest.TestCase):
 def test_unverified_repricing(self):
  r=parse(t(),"a"*64)
  self.assertEqual(r["nine_month_reported_revenue_yoy_pct"],10)
  self.assertFalse(r["audited_income_and_profit_for_new_per_verified"])
  self.assertFalse(r["ranking_eligible"])
 def test_guard_incorrect(self):
  for a,b in [("9M2026 Market Update","FY2025 Report"),
              ("13 November 2026","13 November 2025"),
              ("Growth of 10%","Growth of 1%"),
              ("37.7b","17.7b")]:
   with self.subTest(a=a),self.assertRaises(ValueError):
    parse(t().replace(a,b),"a"*64)
if __name__=="__main__":unittest.main()
