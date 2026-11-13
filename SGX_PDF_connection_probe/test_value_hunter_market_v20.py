import unittest
from value_hunter_market_v20 import join_record

class MarketV20Tests(unittest.TestCase):
    def setUp(self):
        self.fin={'symbol':'S68','fiscal_year':2026,'metrics':{'attributable_profit':{'2026':{'value':500}},'equity':{'2026':{'value':1000}}}}
        self.quote={'price_sgd':2.0,'market_timestamp_utc':'2026-11-12T08:00:00+00:00'}
        self.shares={'symbol':'S68','shares_outstanding':1000000,'as_of_date':'2026-06-30','source_url':'https://example.org/report','verification_status':'INDEPENDENTLY_VERIFIED'}
    def test_no_shares_no_valuation(self):
        r=join_record(self.fin,self.quote)
        self.assertIsNone(r['per']);self.assertIsNone(r['pbr']);self.assertFalse(r['eligible_for_investment_ranking'])
    def test_verified_shares_unit_conversion(self):
        r=join_record(self.fin,self.quote,self.shares)
        self.assertEqual(r['market_cap_sgd'],2000000)
        self.assertEqual(r['per'],4)
        self.assertEqual(r['pbr'],2)
        self.assertFalse(r['eligible_for_investment_ranking'])
    def test_missing_source_rejected(self):
        shares={**self.shares,'source_url':''}
        self.assertIsNone(join_record(self.fin,self.quote,shares)['market_cap_sgd'])
    def test_negative_profit_no_per(self):
        self.fin['metrics']['attributable_profit']['2026']['value']=-500
        r=join_record(self.fin,self.quote,self.shares)
        self.assertIsNone(r['per']);self.assertEqual(r['pbr'],2)

if __name__=='__main__':unittest.main()
