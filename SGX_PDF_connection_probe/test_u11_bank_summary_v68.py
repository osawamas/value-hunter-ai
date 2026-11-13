"""UOB five-year bank summary: historical vs current and unit scale tests."""
import tempfile
import unittest
from pathlib import Path
import fitz
from u11_bank_summary_v68 import parse_pdf, run, EXPECTED

def fake(*,bad_profit=False,bad_year=False,duplicate=False):
    pdf=fitz.open()
    for _ in range(45):pdf.new_page(width=1100,height=900)
    pdf[0].insert_text((20,28),"UOB Annual Report 2025")
    page=pdf[44]
    lines=["Five-Year Group Financial Summary",
           "2020" if bad_year else "2021","2022","2023","2024","2025",
           "Selected Income Statement Items ($ million)",
           "Selected Balance Sheet Items ($ billion)"]
    for key,(label,amounts) in EXPECTED.items():
        vals=list(amounts)
        if bad_profit and key=="operating_profit":
            vals[-1]+=1
        lines.extend([label,*[f"{val:,}" for val in vals]])
        if duplicate and key=="total_income":
            lines.extend([label,*[f"{val:,}" for val in vals]])
    for i,line in enumerate(lines):
        page.insert_text((20,30+18*i),line,fontsize=9)
    data=pdf.tobytes()
    pdf.close()
    return data

class UOBSummaryTests(unittest.TestCase):
    def test_bank_2025_financial_and_rounded_balance_units(self):
        data=parse_pdf(fake())
        self.assertEqual(data["metrics"]["total_income"]["2025"],13808)
        self.assertEqual(data["metrics"]["total_assets_rounded_billions"]["2025"],572)
        self.assertEqual(data["metrics"]["parent_equity_rounded_billions"]["2024"],50)
        self.assertEqual(data["rounded_balance_unit"],"SGD_billions_rounded")
        self.assertFalse(data["ranking_eligible"])
    def test_wrong_profit_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(bad_profit=True))
    def test_wrong_period_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(bad_year=True))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(duplicate=True))
    def test_invalid_source_never_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            record=run(Path(tmp)/"x.json",raw=b"not_pdf")
            self.assertEqual(record["status"],"NOT_VERIFIED")
            self.assertIsNone(record["record"])
if __name__=="__main__":unittest.main()
