"""v44 regression: synthetic PDFs including failure/ambiguity paths."""
import tempfile
import unittest
from pathlib import Path

import fitz

from g13_treasury_v44 import EXPECTED as G13_EXPECTED, parse_pdf as parse_g13, run as run_g13
from s68_official_pdf_v44 import EXPECTED as S68_EXPECTED, parse_pdf as parse_s68, run as run_s68


def g13_document(valid=True):
    pdf = fitz.open()
    page = pdf.new_page(width=900, height=800)
    y = 40
    rows = ["Number of Issued Shares excluding Treasury Shares",
            "Treasury Shares", "12,094,026,824"]
    for year in ("2025", "2024"):
        d = G13_EXPECTED[year]
        rows += [f'{d["outstanding"]:,}', f'{d["treasury"]:,}']
    if not valid:
        rows.remove("8,121,350")
    for line in rows:
        page.insert_text((40, y), line, fontsize=10)
        y += 25
    raw = pdf.tobytes()
    pdf.close()
    return raw


def s68_document(changed=False, duplicate=False):
    pdf = fitz.open()
    for i in range(14):
        page = pdf.new_page(width=900, height=800)
        page.insert_text((20, 25), "Singapore Exchange Limited", fontsize=10)
        page.insert_text((20, 40), "Financial statements", fontsize=10)
        if i != 8:
            continue
        y = 80
        labels = {
            "revenue": "Total operating revenue",
            "operating_profit": "Operating profit",
            "attributable_profit": "Equity holders of the Company",
            "assets": "Total assets",
            "liabilities": "Total liabilities",
            "equity": "Total equity",
        }
        for key, pair in S68_EXPECTED.items():
            val1 = pair[0] + (1 if changed and key == "assets" else 0)
            page.insert_text((20, y), labels[key], fontsize=9)
            page.insert_text((420, y), f"{val1:,}", fontsize=9)
            page.insert_text((560, y), f"{pair[1]:,}", fontsize=9)
            y += 45
        if duplicate:
            page.insert_text((20, y), labels["assets"], fontsize=9)
            page.insert_text((420, y), f'{S68_EXPECTED["assets"][0]:,}', fontsize=9)
            page.insert_text((560, y), f'{S68_EXPECTED["assets"][1]:,}', fontsize=9)
    raw = pdf.tobytes()
    pdf.close()
    return raw


class TreasuryTests(unittest.TestCase):
    def test_two_years_and_treasury_basis(self):
        data = parse_g13(g13_document())
        self.assertEqual(data["2025"]["outstanding"], 12085905474)
        self.assertEqual(data["2024"]["outstanding"], 12072532474)
        self.assertEqual(data["2025"]["share_count_basis"], "issued_excluding_treasury")

    def test_missing_treasury_rejected(self):
        with self.assertRaises(ValueError):
            parse_g13(g13_document(valid=False))

    def test_no_2026_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_g13(Path(temp) / "g13.json", raw=g13_document())
            self.assertFalse(result["latest_2026_snapshot_treasury_basis_verified"])
            self.assertEqual(result["status"], "FY2025_TREASURY_DEDUCTION_ARITHMETIC_MATCHED")


class SGXTests(unittest.TestCase):
    def test_six_group_metrics_and_balance(self):
        metrics = parse_s68(s68_document())
        self.assertEqual(metrics["revenue"]["2026"]["value"], 1559469)
        self.assertEqual(metrics["equity"]["2025"]["value"], 2199921)

    def test_disagreeing_figures_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_s68(s68_document(changed=True))

    def test_ambiguous_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            parse_s68(s68_document(duplicate=True))

    def test_failure_keeps_empty_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_s68(Path(temp) / "s68.json", raw=b"not a pdf")
            self.assertEqual(result["status"], "NOT_VERIFIED")
            self.assertEqual(result["metrics"], {})


if __name__ == "__main__":
    unittest.main()
