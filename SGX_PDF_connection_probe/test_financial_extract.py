import unittest
from financial_extract import extract_s68_fy2026

class Tests(unittest.TestCase):
 def test_valid_statement(self):
  page='FY2026 FY2025\n'+'\n'.join([
   'Operating revenue 823,286 688,398 19.6 1,559,469 1,370,625 13.8',
   'Net revenue 782,921 651,808 20.1 1,478,321 1,298,167 13.9',
   'Operating profit 462,579 359,596 28.6 887,190 742,843 19.4',
   'Profit attributable to equity holders 355,693 307,986 15.5 698,411 647,983 7.8'])
  x=extract_s68_fy2026([page]);self.assertEqual(x['metrics']['operating_profit']['fy2026_sgd_thousands'],887190)
  self.assertAlmostEqual(x['derived']['revenue_growth_pct'],13.782,delta=.05)
 def test_no_data(self):
  with self.assertRaises(ValueError):extract_s68_fy2026(['nothing'])
 def test_half_year_not_fy(self):
  page='2026 2025\nOperating revenue 823,286 688,398\nNet revenue 782,921 651,808\nOperating profit 462,579 359,596\nProfit attributable to equity holders 355,693 307,986'
  with self.assertRaises(ValueError):extract_s68_fy2026([page])
 def test_changed_number_rejected(self):
  page='2026 2025\nOperating revenue 1,559,470 1,370,625\nNet revenue 1,478,321 1,298,167\nOperating profit 887,190 742,843\nProfit attributable to equity holders 698,411 647,983'
  with self.assertRaises(ValueError):extract_s68_fy2026([page])
if __name__=='__main__':unittest.main(verbosity=2)
