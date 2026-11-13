import tempfile
import unittest
from pathlib import Path
import fitz
from o39_bank_summary_v67 import parse_pdf, run, VALUES

def fake(*,wrong_value=False,wrong_year=False,duplicate=False):
    doc=fitz.open()
    for _ in range(98):doc.new_page(width=1100,height=950)
    doc[0].insert_text((20,30),"OCBC Annual Report 2025")
    lines=[
        "Selected Income Statement Items ($ million)",
        "Selected Balance Sheet Items ($ million)",
        "2025" if not wrong_year else "2023",
        "2024",
    ]
    for key,(label,pair) in VALUES.items():
        a,b=pair
        if wrong_value and key=="total_income":a+=1
        lines.extend((label,f"{a:,}",f"{b:,}"))
        if duplicate and key=="parent_equity":
            lines.extend((label,f"{a:,}",f"{b:,}"))
    for i,line in enumerate(lines):
        doc[97].insert_text((20,30+i*20),line,fontsize=9)
    raw=doc.tobytes()
    doc.close()
    return raw

class OCBCBankSummaryTests(unittest.TestCase):
    def test_2025_and_2024_group_highlights(self):
        x=parse_pdf(fake())
        self.assertEqual(x["metrics"]["total_income"]["2025"],14614)
        self.assertEqual(x["metrics"]["net_interest_income"]["2024"],9755)
        self.assertEqual(x["metrics"]["parent_equity"]["2025"],61768)
        self.assertEqual(x["scope"],"ISSUER_SELECTED_GROUP_FINANCIAL_HIGHLIGHTS")
        self.assertFalse(x["ranking_eligible"])
    def test_wrong_total_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(wrong_value=True))
    def test_wrong_period_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(wrong_year=True))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(fake(duplicate=True))
    def test_invalid_pdf_not_promoted(self):
        with tempfile.TemporaryDirectory() as t:
            x=run(Path(t)/"x.json",raw=b"<html>no</html>")
            self.assertEqual(x["status"],"NOT_VERIFIED")
            self.assertIsNone(x["record"])
if __name__=="__main__":unittest.main()
