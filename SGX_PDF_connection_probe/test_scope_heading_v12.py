import unittest
from scope_heading_v12 import classify_heading, inspect

class HeadingTests(unittest.TestCase):
    def test_explicit_group(self): self.assertEqual(classify_heading('CONSOLIDATED STATEMENT OF FINANCIAL POSITION'),'consolidated')
    def test_explicit_company(self): self.assertEqual(classify_heading('COMPANY STATEMENT OF FINANCIAL POSITION'),'company')
    def test_ambiguous(self): self.assertIsNone(classify_heading('GROUP AND COMPANY STATEMENTS OF FINANCIAL POSITION'))
    def test_no_heading(self): self.assertIsNone(classify_heading('Company subsidiaries'))
    def test_prior_page_not_proof(self):
        r=inspect(['Consolidated statement of financial position\n','Total assets 123\n'],[2])
        self.assertEqual(r['page_scope_evidence'][0]['scope'],'unclassified')
    def test_same_page_heading(self):
        r=inspect(['Company statement of financial position\nTotal assets 123'],[1])
        self.assertEqual(r['page_scope_evidence'][0]['scope'],'company')
    def test_out_of_range(self):
        self.assertEqual(inspect(['x'],[3])['page_scope_evidence'][0]['status'],'PAGE_OUT_OF_RANGE')

if __name__=='__main__': unittest.main()
