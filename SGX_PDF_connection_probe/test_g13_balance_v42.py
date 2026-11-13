"""Consolidated 2025/2024 G13 segment-note balance tests, using synthetic PDF."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import fitz

from g13_balance_v42 import parse_pdf, run, extract_half

VALUE = {
    "2025": {"assets": 9185799, "liabilities": 980383, "equity": 8205416},
    "2024": {"assets": 9230564, "liabilities": 932987, "equity": 8297577},
}

def synthetic_pdf(*, break_balance=False, company_header=False, missing_liability=False):
    doc = fitz.open()
    for i in range(62):
        page = doc.new_page(width=900, height=650)
        if i == 35:
            page.insert_text((18, 90), "Equity attributable to ordinary shareholders", fontsize=9)
        if i != 61:
            continue
        for year, x in [(2025, 18), (2024, 468)]:
            page.insert_text((x, 34), "27. SEGMENT INFORMATION (CONTINUED)", fontsize=10)
            page.insert_text((x, 58), "Company" if company_header and year == 2025 else "Group", fontsize=10)
            page.insert_text((x, 73), str(year), fontsize=10)
            page.insert_text((x + 4, 190), "Assets", fontsize=9)
            page.insert_text((x + 4, 228), "Consolidated total assets", fontsize=9)
            page.insert_text((x + 318, 228),
                             format(VALUE[str(year)]["assets"] + (1 if break_balance and year == 2025 else 0), ","),
                             fontsize=9)
            page.insert_text((x + 4, 292), "Liabilities", fontsize=9)
            if not missing_liability:
                page.insert_text((x + 4, 328), "Consolidated total liabilities", fontsize=9)
                page.insert_text((x + 318, 328), format(VALUE[str(year)]["liabilities"], ","), fontsize=9)
    result = doc.tobytes()
    doc.close()
    return result

def upstream(pdf):
    return {"symbol": "G13", "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
            "data": {"balance": {"equity": {"scope": "Group",
                "periods": {year: {"value": values["equity"]}
                            for year, values in VALUE.items()}}}}}

class G13BalanceTests(unittest.TestCase):
    def test_two_group_years_extracted_with_balancing(self):
        parsed = parse_pdf(synthetic_pdf(), {y: v["equity"] for y, v in VALUE.items()})
        self.assertEqual(parsed["metrics"]["assets"]["2025"]["value"], 9185799)
        self.assertEqual(parsed["metrics"]["liabilities"]["2024"]["value"], 932987)
        self.assertEqual(parsed["metrics"]["parent_equity"]["2025"]["value"], 8205416)
        self.assertEqual(parsed["page_pdf_number"], 62)
        self.assertEqual(parsed["checks"]["2025"]["assets_minus_liabilities_minus_equity"], 0)
        self.assertEqual(parsed["checks"]["2024"]["assets_minus_liabilities_minus_equity"], 0)

    def test_reject_company_scope(self):
        with self.assertRaises(ValueError):
            parse_pdf(synthetic_pdf(company_header=True),
                      {y: v["equity"] for y, v in VALUE.items()})

    def test_reject_arithmetic_mismatch(self):
        with self.assertRaisesRegex(ValueError, "equation mismatch"):
            parse_pdf(synthetic_pdf(break_balance=True),
                      {y: v["equity"] for y, v in VALUE.items()})

    def test_reject_missing_liabilities(self):
        with self.assertRaises(ValueError):
            parse_pdf(synthetic_pdf(missing_liability=True),
                      {y: v["equity"] for y, v in VALUE.items()})

    def test_no_unsupported_pdf(self):
        with self.assertRaises(ValueError):
            parse_pdf(b"fake", {y: v["equity"] for y, v in VALUE.items()})

    def test_sha_source_identical(self):
        pdf = synthetic_pdf()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/"g13.json"
            dest = Path(temp)/"balance.json"
            source.write_text(json.dumps(upstream(pdf)), encoding="utf-8")
            result = run(source, dest, raw=pdf)
            self.assertEqual(result["status"], "EXTRACTED_GROUP_BALANCE_ARITHMETIC_MATCHED")
            self.assertEqual(result["metrics"]["assets"]["2025"]["value"], 9185799)

    def test_pdf_digest_mismatch_is_not_accepted(self):
        pdf = synthetic_pdf()
        upstream_data = upstream(pdf)
        upstream_data["pdf_sha256"] = "wrong"
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/"g13.json"
            dest = Path(temp)/"balance.json"
            source.write_text(json.dumps(upstream_data), encoding="utf-8")
            result = run(source, dest, raw=pdf)
            self.assertEqual(result["status"], "NOT_VERIFIED")
            self.assertEqual(result["metrics"], {})
            self.assertIn("SHA256", result["error"])

if __name__ == "__main__":
    unittest.main()
