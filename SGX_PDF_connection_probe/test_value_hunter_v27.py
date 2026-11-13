import tempfile
import unittest
from pathlib import Path
import fitz
from value_hunter_v27 import extract_pdf, extract_from_rows, group_lines, parse_amount, run


class V27Tests(unittest.TestCase):
    def test_amount(self):
        self.assertEqual(parse_amount("(249,133)"), -249133)
        self.assertIsNone(parse_amount("2025a"))
        self.assertIsNone(parse_amount("(123"))
        self.assertIsNone(parse_amount("123)"))
        self.assertEqual(parse_amount("-123"), -123)

    def test_year_column_not_value_order(self):
        rows = group_lines([
            (170, 10, 190, 20, "2024", 0, 0, 0),
            (280, 10, 300, 20, "2025", 0, 0, 0),
            (10, 35, 70, 45, "Revenue", 0, 0, 0),
            (170, 35, 220, 45, "2,529,960", 0, 0, 0),
            (280, 35, 330, 45, "2,452,053", 0, 0, 0),
        ])
        value, count = extract_from_rows(rows, "G13", "revenue")
        self.assertEqual(value["value"], 2452053)

    def test_s20_selects_full_year_not_half_year(self):
        rows = group_lines([
            (40, 3, 95, 11, "12 months", 0, 0, 0),
            (100, 10, 130, 19, "2025", 0, 0, 0),
            (200, 10, 230, 19, "2024", 0, 0, 0),
            (300, 10, 330, 19, "2025", 0, 0, 0),
            (400, 10, 430, 19, "2024", 0, 0, 0),
            (15, 35, 75, 45, "Revenue", 0, 0, 0),
            (100, 35, 150, 45, "355,783", 0, 0, 0),
            (200, 35, 250, 45, "312,091", 0, 0, 0),
            (300, 35, 350, 45, "623,300", 0, 0, 0),
            (400, 35, 450, 45, "564,627", 0, 0, 0),
        ])
        value, count = extract_from_rows(rows, "S20", "revenue")
        self.assertEqual(count, 1)
        self.assertEqual(value["value"], 623300)

    def test_s20_refuses_ambiguous_period(self):
        rows = group_lines([
            (100, 10, 130, 19, "2025", 0, 0, 0),
            (200, 10, 230, 19, "2024", 0, 0, 0),
            (300, 10, 330, 19, "2025", 0, 0, 0),
            (400, 10, 430, 19, "2024", 0, 0, 0),
            (15, 35, 75, 45, "Revenue", 0, 0, 0),
            (100, 35, 150, 45, "355,783", 0, 0, 0),
            (200, 35, 250, 45, "312,091", 0, 0, 0),
            (300, 35, 350, 45, "623,300", 0, 0, 0),
            (400, 35, 450, 45, "564,627", 0, 0, 0),
        ])
        self.assertEqual(extract_from_rows(rows, "S20", "revenue"), (None, 0))

    def test_no_year_no_certification(self):
        rows = group_lines([
            (10, 35, 70, 45, "Revenue", 0, 0, 0),
            (170, 35, 220, 45, "2,529,960", 0, 0, 0),
            (280, 35, 330, 45, "2,452,053", 0, 0, 0),
        ])
        self.assertEqual(extract_from_rows(rows, "G13", "revenue"), (None, 0))

    def test_pdf_roundtrip(self):
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((180, 50), "2024")
        page.insert_text((290, 50), "2025")
        page.insert_text((25, 85), "Revenue")
        page.insert_text((180, 85), "2,529,960")
        page.insert_text((290, 85), "2,452,053")
        result = extract_pdf(doc.tobytes(), "G13")
        self.assertEqual(result["revenue"]["value"], 2452053)

    def test_missing_live_pdf_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            def offline(url):
                raise OSError("offline")
            result = run({"records": []}, directory, fetch=offline)
            self.assertEqual(result["ranking_eligible_count"], 0)
            self.assertEqual(sum(bool(row.get("error")) for row in result["records"]), 2)
            self.assertTrue(Path(directory, "audit_v27.json").exists())


if __name__ == "__main__":
    unittest.main()
