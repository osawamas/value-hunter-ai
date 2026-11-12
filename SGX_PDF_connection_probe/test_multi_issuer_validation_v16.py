import unittest
from multi_issuer_validation_v16 import classify
class Tests(unittest.TestCase):
    def test_no_false_verification(self):
        d={'symbol':'X','issuer':'Example','source_url':'https://example.com','pdf_sha256':'abc','evidence':[
          {'page':1,'line':1,'labels':['revenue'],'text':'Revenue','context':'Revenue | 1,234 | 1,000'},
          {'page':1,'line':2,'labels':['operating_profit'],'text':'Operating profit','context':'Operating profit | 2,234 | 2,000'}]}
        rows=classify(d)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['status']=='CANDIDATE_NOT_VERIFIED' for r in rows))
    def test_reject_notes_subtotal(self):
        d={'symbol':'X','issuer':'Example','source_url':'x','pdf_sha256':'x','evidence':[
          {'page':1,'line':1,'labels':['total_assets'],'text':'Total assets less current liabilities','context':'1,234'},
          {'page':1,'line':2,'labels':['total_equity'],'text':'Total equity','context':'2,345'}]}
        self.assertEqual(len(classify(d)),1)
    def test_single_metric_not_statement(self):
        d={'symbol':'X','issuer':'Example','source_url':'x','pdf_sha256':'x','evidence':[
          {'page':1,'line':1,'labels':['revenue'],'text':'Revenue','context':'1,234'}]}
        self.assertEqual(classify(d),[])
if __name__=='__main__': unittest.main()
