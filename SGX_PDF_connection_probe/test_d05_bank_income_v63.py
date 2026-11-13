"""DBS bank-specific income statement tests, no invented valuation data."""
import tempfile
import unittest
from pathlib import Path
import fitz
from d05_bank_income_v63 import parse_pdf, run, EXPECTED, ROW


def make_pdf(*,wrong_profit=False,wrong_year=False,duplicate=False):
    doc=fitz.open()
    for _ in range(58):
        doc.new_page(width=1100,height=1100)
    doc[0].insert_text((20,30),"DBS Group Holdings Ltd Annual Report 2025")
    page=doc[57]
    lines=["DBS Group Holdings Ltd and its Subsidiaries",
           "Consolidated income statement",
           "for the year ended 31 December "+("2024" if wrong_year else "2025"),
           "In $ millions","Note","2025","2024"]
    for key,label in ROW.items():
        a,b=EXPECTED[key]
        if key=="net_profit" and wrong_profit:a+=1
        lines.extend((label,f"{a:,}",f"{b:,}"))
        if duplicate and key=="total_income":
            lines.extend((label,f"{a:,}",f"{b:,}"))
    lines.append("Consolidated statement of comprehensive income")
    for i,line in enumerate(lines):
        page.insert_text((20,35+i*22),line,fontsize=9)
    raw=doc.tobytes()
    doc.close()
    return raw


class IncomeTests(unittest.TestCase):
    def test_bank_income_statement_two_years(self):
        r=parse_pdf(make_pdf())
        self.assertEqual(r["metrics"]["total_income"]["2025"],22900)
        self.assertEqual(r["metrics"]["net_interest_income"]["2024"],14424)
        self.assertEqual(r["metrics"]["profit_attributable_to_parent"]["2025"],10933)
        self.assertEqual(r["industry_metric_schema"],"BANKING_INCOME_V63_NOT_INDUSTRIAL")
        self.assertFalse(r["ranking_eligible"])
    def test_reject_changed_profit(self):
        with self.assertRaises(ValueError):parse_pdf(make_pdf(wrong_profit=True))
    def test_reject_wrong_date(self):
        with self.assertRaises(ValueError):parse_pdf(make_pdf(wrong_year=True))
    def test_reject_duplicate_income_row(self):
        with self.assertRaises(ValueError):parse_pdf(make_pdf(duplicate=True))
    def test_invalid_pdf_not_promoted(self):
        with tempfile.TemporaryDirectory() as t:
            r=run(Path(t)/"income.json",raw=b"not pdf")
            self.assertEqual(r["status"],"NOT_VERIFIED")
            self.assertIsNone(r["record"])

if __name__=="__main__":
    unittest.main()
