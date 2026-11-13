import unittest
from value_hunter_shares_v21 import calc
class Tests(unittest.TestCase):
 def setUp(self):
  self.fin={'symbol':'X','fiscal_year':2025,'metrics':{'attributable_profit':{'2025':{'value':1000}},'equity':{'2025':{'value':2000}}}}
  self.market={'price':{'price_sgd':2,'market_timestamp_utc':'2026-11-13T01:00:00+00:00'}}
  self.shares={'shares_outstanding':1000000,'as_of_date':'2026-10-01','source_url':'https://example.org'}
 def test_math(self):
  r=calc(self.fin,self.market,self.shares);self.assertEqual(r['market_cap_sgd'],2000000);self.assertEqual(r['per_estimate'],2);self.assertEqual(r['pbr_estimate'],1);self.assertFalse(r['ranking_eligible'])
 def test_no_shares(self): self.assertIsNone(calc(self.fin,self.market,None)['market_cap_sgd'])
 def test_future_shares(self):
  s=dict(self.shares,as_of_date='2027-01-01');self.assertIsNone(calc(self.fin,self.market,s)['market_cap_sgd'])
 def test_negative_profit(self):
  f=dict(self.fin,metrics={'attributable_profit':{'2025':{'value':-2}},'equity':{'2025':{'value':2000}}});self.assertIsNone(calc(f,self.market,self.shares)['per_estimate'])
if __name__=='__main__':unittest.main()
