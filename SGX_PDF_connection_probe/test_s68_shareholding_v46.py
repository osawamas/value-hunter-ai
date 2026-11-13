"""Synthetic S68 shareholding page tests: date, arithmetic, missing fields."""
import tempfile
import unittest
from pathlib import Path
import fitz
from s68_shareholding_v46 import parse_pdf, run

def pdf_of(*, bad_date=False, bad_total=False):
    doc=fitz.open()
    p=doc.new_page(width=900,height=950)
    rows=[
        "Statistics of Shareholdings",
        "as at 1 September 2025" if bad_date else "as at 1 September 2026",
        "Number of Issued and Paid-up Shares: 1,071,642,400",
        "No. of shares (excluding treasury shares)",
        "Total 31,123 100.00 "+("1,070,843,483" if bad_total else "1,070,843,484")+" 100.00",
        "Treasury shares and subsidiary holdings",
        "Number of treasury shares: 798,916",
    ]
    for i,line in enumerate(rows):
        p.insert_text((25,50+40*i),line,fontsize=11)
    data=doc.tobytes()
    doc.close()
    return data

class S68SharesTests(unittest.TestCase):
    def test_valid(self):
        s=parse_pdf(pdf_of())
        self.assertEqual(s["shares_outstanding"],1070843484)
        self.assertEqual(s["page_pdf_number"],1)
        self.assertEqual(s["as_of_date"],"2026-09-01")
    def test_wrong_date(self):
        with self.assertRaises(ValueError):parse_pdf(pdf_of(bad_date=True))
    def test_wrong_arithmetic(self):
        with self.assertRaises(ValueError):parse_pdf(pdf_of(bad_total=True))
    def test_failure_does_not_persist_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            rec=run(Path(temp)/"result.json",raw=b"not PDF")
            self.assertIsNone(rec["snapshot"])
            self.assertEqual(rec["status"],"NOT_VERIFIED")
if __name__=="__main__":unittest.main()
