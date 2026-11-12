import unittest
from value_hunter_v19 import ratio,derive
class TestIntegration(unittest.TestCase):
 def test_percent(self):self.assertEqual(ratio(20,100),20)
 def test_zero(self):self.assertIsNone(ratio(1,0))
 def test_missing_data(self):
  r=derive({'symbol':'G13','fiscal_year':2025,'metrics':{}})
  self.assertIsNone(r['derived']['per']);self.assertIsNone(r['derived']['operating_margin_pct']);self.assertFalse(r['quality']['eligible_for_investment_ranking'])
 def test_negative_profit_not_growth(self):
  r=derive({'symbol':'S20','fiscal_year':2025,'metrics':{'attributable_profit':{'2025':{'value':-249133},'2024':{'value':-7226}}}})
  self.assertIsNone(r['derived']['attributable_profit_growth_pct'])
if __name__=='__main__':unittest.main()
