import unittest
from integrated_financial_v14 import integrate

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.b = {'financial_validation':'VERIFIED_CONSOLIDATED_BALANCE_SHEET_ONLY', 'document_id':'S68_FY2026_results', 'consolidated_balance_sheet':{'fiscal_years':[2026,2025], 'currency':'SGD', 'unit_multiplier':1000, 'heading':'Statement of Financial Position - Group', 'page':13, 'values_thousands_sgd':{'assets':[4547470,4143988], 'liabilities':[2184488,1944067], 'equity':[2362982,2199921]}}}
        self.i = {'ticker':'S68','fiscal_year':2026,'period':'FY','consolidation':'Group','currency':'SGD','unit':'SGD_thousands','status':'verified_against_known_S68_FY2026_values','metrics':{k:{'fy2026_sgd_thousands':a,'fy2025_sgd_thousands':b,'page':9} for k,a,b in [('operating_revenue',1559469,1370625),('net_revenue',1478321,1298167),('operating_profit',887190,742843),('profit_attributable',698411,647983)]}}
    def test_valid(self):
        r=integrate(self.b,self.i)
        self.assertEqual(r['balance_sheet']['assets'][0],4547470)
        self.assertAlmostEqual(r['derived']['revenue_growth_pct'],13.7779,places=2)
    def test_wrong_scope(self):
        self.b['consolidated_balance_sheet']['heading']='Company'
        with self.assertRaises(ValueError):integrate(self.b,self.i)
    def test_wrong_year(self):
        self.i['fiscal_year']=2025
        with self.assertRaises(ValueError):integrate(self.b,self.i)
    def test_bad_balance(self):
        self.b['consolidated_balance_sheet']['values_thousands_sgd']['assets'][0]+=1
        with self.assertRaises(ValueError):integrate(self.b,self.i)
    def test_unverified_income(self):
        self.i['status']='unverified'
        with self.assertRaises(ValueError):integrate(self.b,self.i)
    def test_missing_metric(self):
        del self.i['metrics']['operating_profit']
        with self.assertRaises(ValueError):integrate(self.b,self.i)

if __name__=='__main__':unittest.main()
