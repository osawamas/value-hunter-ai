"""Synthetic audited table regression tests for S63 annual report."""
import unittest
import fitz
from s63_audited_pdf_v32 import parse_document, amount, run

DATA = {
  "income": [
    ("Revenue", "12,346,426", "11,275,659"),
    ("Cost of sales", "(10,187,924)", "(9,101,384)"),
    ("Gross profit", "2,158,502", "2,174,275"),
    ("Profit from operations", "843,116", "1,005,540"),
    ("Profit after taxation", "495,786", "729,205"),
    ("Attributable to:", None, None),
    ("Shareholders of the Company", "462,770", "702,256"),
    ("Non-controlling interests", "33,016", "26,949"),
  ],
  "assets": [("Total assets", "16,032,106", "16,221,299")],
  "liabilities": [
    ("Total liabilities", "13,110,861", "13,270,452"),
    ("Equity attributable to owners of the Company", "2,573,638", "2,670,373"),
    ("Total equity", "2,921,245", "2,950,847"),
  ],
}

def make_pdf(*, wrong_balance=False, omit_years=False):
    pdf = fitz.open()
    headings = {
        "income": "CONSOLIDATED INCOME STATEMENT",
        "assets": "CONSOLIDATED STATEMENT OF FINANCIAL POSITION",
        "liabilities": "CONSOLIDATED STATEMENT OF FINANCIAL POSITION",
    }
    for kind in ("income", "assets", "liabilities"):
        p = pdf.new_page(width=600, height=800)
        p.insert_text((20, 36), headings[kind], fontsize=14)
        p.insert_text((20, 55), "Group", fontsize=10)
        if not omit_years:
            p.insert_text((305, 62), "2025", fontsize=10)
            p.insert_text((440, 62), "2024", fontsize=10)
        y = 95
        for label, v25, v24 in DATA[kind]:
            if label == "Total equity" and wrong_balance:
                v25 = "2,921,246"
            p.insert_text((20, y), label, fontsize=9)
            if v25:
                p.insert_text((305, y), v25, fontsize=9)
                p.insert_text((440, y), v24, fontsize=9)
            y += 24
    output = pdf.tobytes()
    pdf.close()
    return output

class S63Tests(unittest.TestCase):
    def test_negative_amount(self):
        self.assertEqual(amount("(10,187,924)"), -10187924)
        self.assertIsNone(amount("2025year"))

    def test_audited_2025_2024_tables(self):
        result = parse_document(make_pdf())
        self.assertEqual(result["status"], "EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED")
        rec = result["record"]
        self.assertEqual(rec["metrics"]["revenue"]["2025"]["value"], 12346426)
        self.assertEqual(rec["metrics"]["operating_profit"]["2025"]["value"], 843116)
        self.assertEqual(rec["metrics"]["attributable_profit"]["2025"]["value"], 462770)
        self.assertEqual(rec["metrics"]["parent_equity"]["2025"]["value"], 2573638)
        self.assertEqual(rec["metrics"]["assets"]["2025"]["value"], 16032106)
        self.assertEqual(rec["metrics"]["equity"]["2024"]["value"], 2950847)
        self.assertEqual(result["financial_checks"]["2025"]["balance_difference"], 0)
        self.assertEqual(result["financial_checks"]["2024"]["profit_attribution_difference"], 0)

    def test_arithmetic_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            parse_document(make_pdf(wrong_balance=True))

    def test_missing_year_header_rejected(self):
        with self.assertRaises(ValueError):
            parse_document(make_pdf(omit_years=True))

    def test_not_a_pdf_rejected(self):
        with self.assertRaises(ValueError):
            parse_document(b"not a pdf")

    def test_failure_does_not_invent_record(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"s63.json"
            result = run(path, document=make_pdf(wrong_balance=True))
            self.assertIsNone(result["record"])
            self.assertEqual(result["status"], "NOT_VERIFIED")
            self.assertIsNone(json.loads(path.read_text())["record"])

if __name__ == "__main__":
    unittest.main()
