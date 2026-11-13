import tempfile
import unittest
from pathlib import Path
import fitz
from s68_annual_crosscheck_v50 import parse_pdf,run

def sample(wrong=False,duplicate=False):
    doc=fitz.open()
    for repeat in range(2 if duplicate else 1):
        p=doc.new_page(width=1000,height=650)
        lines=[
            "Statement of comprehensive income",
            "For the financial year ended 30 June 2026",
            "Group 2026 2025",
            "Operating revenue 1,559,469 "+("1,370,624" if wrong else "1,370,625"),
            "Equity holders of the Company 698,411 647,983",
        ]
        for i,line in enumerate(lines):
            p.insert_text((20,40+i*55),line,fontsize=10)
    b=doc.tobytes()
    doc.close()
    return b

class S68CrossCheckTests(unittest.TestCase):
    def test_match(self):
        v=parse_pdf(sample())
        self.assertEqual(v["revenue"][0]["2026"],1559469)
        self.assertEqual(v["attributable_profit"][0]["2025"],647983)
    def test_mismatch_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(sample(wrong=True))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(sample(duplicate=True))
    def test_no_pdf_keeps_empty(self):
        with tempfile.TemporaryDirectory() as d:
            x=run(Path(d)/"x.json",raw=b"not pdf")
            self.assertEqual(x["checks"],[])
            self.assertEqual(x["status"],"NOT_VERIFIED")

if __name__=="__main__":unittest.main()
