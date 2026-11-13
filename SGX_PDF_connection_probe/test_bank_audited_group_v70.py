"""v70 audited bank Group income/balance fail-closed synthetic regression tests."""
import unittest
import tempfile
from pathlib import Path
import fitz
from bank_audited_group_v70 import VALUES,parse_pdf,run


def make_pdf(symbol,*,bad_income=False,bad_balance=False,
             wrong_date=False,duplicate=False,standalone=False):
    spec=VALUES[symbol]
    pdf=fitz.open()
    for _ in range(spec["pages"][1]):
        pdf.new_page(width=1200,height=2100)
    pdf[0].insert_text((20,25),"OCBC annual report" if symbol=="O39" else "UOB annual report")
    for kind,page_number in (("income",spec["pages"][0]),("balance",spec["pages"][1])):
        page=pdf[page_number-1]
        heading="Income Statements" if kind=="income" else "Balance Sheets"
        date="31 December 2024" if wrong_date else "31 December 2025"
        lines=[heading,"For the year ended "+date,
               "The Bank" if standalone else "The Group","The Bank",
               "In $ million","2025","2024"]
        for key,(label,pair) in spec[kind].items():
            a,b=pair
            if bad_income and kind=="income" and key=="total_income":a+=1
            if bad_balance and kind=="balance" and key=="total_assets":a+=1
            def fmt(v):
                return f"({-v:,})" if v<0 else ("–" if v==0 else f"{v:,}")
            lines.extend((label,fmt(a),fmt(b)))
            if duplicate and kind=="income" and key=="total_income":
                lines.extend((label,fmt(a),fmt(b)))
        for i,line in enumerate(lines):
            page.insert_text((20,28+i*24),line,fontsize=9)
    data=pdf.tobytes()
    pdf.close()
    return data


class OCBCGroupTests(unittest.TestCase):
    def test_income_balance_and_nci(self):
        result=parse_pdf("O39",make_pdf("O39"))
        self.assertEqual(result["balance"]["parent_equity"]["2025"],61768)
        self.assertEqual(result["balance"]["total_assets"]["2025"],675688)
        self.assertEqual(result["income"]["parent_profit"]["2024"],7587)
        self.assertFalse(result["ranking_eligible"])
    def test_income_mismatch(self):
        with self.assertRaises(ValueError):parse_pdf("O39",make_pdf("O39",bad_income=True))
    def test_assets_mismatch(self):
        with self.assertRaises(ValueError):parse_pdf("O39",make_pdf("O39",bad_balance=True))
    def test_standalone_bank_not_group(self):
        with self.assertRaises(ValueError):parse_pdf("O39",make_pdf("O39",standalone=True))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):parse_pdf("O39",make_pdf("O39",duplicate=True))


class UOBGroupTests(unittest.TestCase):
    def test_precise_group_equity_not_rounded(self):
        result=parse_pdf("U11",make_pdf("U11"))
        self.assertEqual(result["balance"]["total_assets"]["2025"],572061)
        self.assertEqual(result["balance"]["parent_equity"]["2025"],51248)
        self.assertEqual(result["balance"]["non_controlling_equity"]["2025"],245)
        self.assertEqual(result["unit"],"SGD_millions")
    def test_group_balance_mismatch(self):
        with self.assertRaises(ValueError):parse_pdf("U11",make_pdf("U11",bad_balance=True))
    def test_period_mismatch(self):
        with self.assertRaises(ValueError):parse_pdf("U11",make_pdf("U11",wrong_date=True))
    def test_source_not_pdf_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=run("U11",Path(tmp)/"bad.json",raw=b"wrong")
            self.assertEqual(r["status"],"NOT_VERIFIED")
            self.assertIsNone(r["record"])


if __name__=="__main__":
    unittest.main()
