import tempfile
import unittest
from pathlib import Path
import fitz
from value_hunter_v27 import extract_pdf, extract_from_rows, group_lines, parse_amount, run


class V27Tests(unittest.TestCase):
    def test_amount(self):
        self.assertEqual(parse_amount("(249,133)"), -249133)
        self.assertIsNone(parse_amount("2025a"))

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
