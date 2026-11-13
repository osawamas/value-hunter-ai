"""D05 banking balance sheet Group-vs-Company and arithmetic regression tests."""
import tempfile
import unittest
from pathlib import Path
import fitz
from d05_bank_balance_v64 import parse_pdf, run, EXPECTED, LABELS


def pdf(*,wrong_assets=False, wrong_parent=False, wrong_year=False, duplicate=False):
    doc=fitz.open()
    for _ in range(61):
        doc.new_page(width=1100,height=1000)
    doc[0].insert_text((20,35),"DBS Annual Report FY2025")
    for index in ([59,60] if duplicate else [59]):
        page=doc[index]
        lines=["DBS Group Holdings Ltd and its Subsidiaries",
               "Balance sheets","as at 31 December "+("2024" if wrong_year else "2025"),
               "In $ millions","Note The Group The Company","2025","2024"]
        for key,label in LABELS.items():
            a,b=EXPECTED[key]
            if wrong_assets and key=="total_assets":a+=1
            if wrong_parent and key=="parent_shareholders_funds":a+=1
            lines.extend([label,f"{a:,}",f"{b:,}"])
        for i,line in enumerate(lines):
            page.insert_text((20,32+20*i),line,fontsize=10)
    data=doc.tobytes()
    doc.close()
    return data


class BalanceTests(unittest.TestCase):
    def test_two_years_and_parent_nci(self):
        x=parse_pdf(pdf())
        self.assertEqual(x["metrics"]["total_assets"]["2025"],897488)
        self.assertEqual(x["metrics"]["parent_shareholders_funds"]["2024"],68786)
        self.assertEqual(x["metrics"]["non_controlling_interests"]["2025"],49)
        self.assertFalse(x["ranking_eligible"])
    def test_assets_mismatch_fails(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(wrong_assets=True))
    def test_parent_mismatch_fails(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(wrong_parent=True))
    def test_wrong_period_fails(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(wrong_year=True))
    def test_two_balance_pages_fails(self):
        with self.assertRaises(ValueError):parse_pdf(pdf(duplicate=True))
    def test_invalid_source_no_record(self):
        with tempfile.TemporaryDirectory() as t:
            x=run(Path(t)/"x.json",raw=b"HTML")
            self.assertEqual(x["status"],"NOT_VERIFIED")
            self.assertIsNone(x["record"])
if __name__=="__main__":unittest.main()
