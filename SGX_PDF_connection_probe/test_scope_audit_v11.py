import unittest
from scope_audit_v11 import audit_pages, context_for_page
class ScopeTests(unittest.TestCase):
    def test_scope_words_are_not_certification(self):
        pages=['Consolidated Statement of Financial Position\nGroup\n2026 2025\nS$\'000\nTotal assets 100 90\nTotal liabilities 30 20\nTotal equity 70 70']
        r=audit_pages(pages,[1]);self.assertEqual(r['financial_validation'],'NOT_VERIFIED')
        self.assertEqual(r['page_scope_evidence'][0]['scope'],'unclassified')
        self.assertIn('group',r['page_scope_evidence'][0]['scope_words'])
    def test_missing_header(self):
        r=audit_pages(['Total assets 100 90'],[1]);self.assertEqual(r['page_scope_evidence'][0]['scope_words'],[])
    def test_empty_page(self):
        self.assertEqual(context_for_page('hello',1),[])
    def test_mixed_headers(self):
        r=audit_pages(['Group Company\nTotal equity 5 6'],[1]);self.assertEqual(r['page_scope_evidence'][0]['scope'],'unclassified')
if __name__=='__main__':unittest.main()
