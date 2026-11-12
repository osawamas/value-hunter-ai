import io
import unittest
import fitz
from multi_issuer_v15 import audit_pdf, validate_manifest

class Tests(unittest.TestCase):
    def test_https_allowlist(self):
        with self.assertRaises(ValueError):
            validate_manifest([{'issuer':'X','symbol':'X','url':'http://links.sgx.com/x'}])
    def test_reject_untrusted_host(self):
        with self.assertRaises(ValueError):
            validate_manifest([{'issuer':'X','symbol':'X','url':'https://example.com/x.pdf'}])
    def test_pdf_evidence_not_verified(self):
        doc = fitz.open(); page = doc.new_page(); page.insert_text((40,70),'Consolidated Statement of Financial Position'); page.insert_text((40,90),'Total assets 1,000 900'); page.insert_text((40,110),'Total liabilities 300 250')
        pdf = doc.tobytes()
        result = audit_pdf(pdf, {'issuer':'Test','symbol':'TST','url':'https://links.sgx.com/example'})
        self.assertEqual(result['status'], 'CANDIDATES_ONLY_NOT_VERIFIED')
        self.assertGreaterEqual(result['evidence_count'], 2)
    def test_required_fields(self):
        with self.assertRaises(ValueError):
            validate_manifest([{'symbol':'X','url':'https://links.sgx.com/a'}])

if __name__ == '__main__': unittest.main()
