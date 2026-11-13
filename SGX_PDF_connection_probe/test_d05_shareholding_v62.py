"""v62 synthetic DBS shareholding PDF tests — never claim live price."""
import tempfile
import unittest
from pathlib import Path
import fitz
from d05_shareholding_v62 import parse_pdf, run


def pdf(*, wrong_net=False, wrong_date=False, duplicate=False):
    doc=fitz.open()
    for _ in range(54):
        doc.new_page(width=1000,height=700)
    pages=[52,53] if duplicate else [52]
    for page_no in pages:
        page=doc[page_no]
        lines=[
            "Shareholding statistics",
            "as at 10 February 2025" if wrong_date else "as at 10 February 2026",
            "Total number of issued ordinary shares – "+("2,837,558,045" if wrong_net else "2,837,558,046")+" (excluding treasury shares)",
            "Treasury Shares – 113,424 (representing 0.004%)",
        ]
        for i,line in enumerate(lines):
            page.insert_text((30,60+i*48),line,fontsize=12)
    doc[0].insert_text((30,30),"DBS Annual Report 2025")
    raw=doc.tobytes()
    doc.close()
    return raw


class DBSTests(unittest.TestCase):
    def test_derived_gross_and_date(self):
        d=parse_pdf(pdf())
        self.assertEqual(d["shares_outstanding"],2837558046)
        self.assertEqual(d["treasury_shares"],113424)
        self.assertEqual(d["issued_shares_including_treasury_derived"],2837671470)
        self.assertEqual(d["as_of_date"],"2026-02-10")
        self.assertFalse(d["quote_data_available"])
        self.assertFalse(d["investment_ranking_eligible"])

    def test_changed_shares_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(wrong_net=True))

    def test_old_period_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(wrong_date=True))

    def test_two_matching_pages_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(duplicate=True))

    def test_invalid_pdf_does_not_promote(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(Path(d)/"dbs.json",raw=b"bad")
            self.assertEqual(r["status"],"NOT_VERIFIED")
            self.assertIsNone(r["snapshot"])

if __name__=="__main__":
    unittest.main()
