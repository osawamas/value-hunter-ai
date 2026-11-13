import tempfile
import unittest
from pathlib import Path
import fitz

from value_hunter_s63_crosscheck_v40 import from_pdf, compare, join, extract_reported


def pdf_fixture(*, reported=True, bad_header=False, missing=False, bop_on_second=False):
    document = fitz.open()
    first = document.new_page()
    first.insert_text((20, 30), "CONTENTS")
    page = document.new_page(width=900, height=800)
    title = ("CONSOLIDATED BASE OPERATING PERFORMANCE (BOP) UNAUDITED"
             if bop_on_second else "CONSOLIDATED INCOME STATEMENT FY 2025 (REPORTED)")
    page.insert_text((20, 25), title, fontsize=11)
    xs = [250, 350, 475, 590]
    for x, year in zip(xs, ["2H2025", "2H2024", "FY2025", "FY2024"]):
        page.insert_text((x, 76), ("2023" if year=="FY2025" and bad_header else year), fontsize=9)
    for label, data, y in [
        ("Revenue", [6430472, 5755265, 12346426, 11275659], 115),
        ("Profit from operations", [280245, 520985, 843116, 1005540], 145),
        ("Profit after taxation", [81620, 381007, 495786, 729205], 180),
        ("Attributable to:", [None]*4, 215),
        ("Shareholders of the Company", [59941, 365728, 462770, 702256], 245),
    ]:
        if missing and label == "Revenue":
            continue
        page.insert_text((20, y), label, fontsize=9)
        for x, v in zip(xs, data):
            if v is not None:
                page.insert_text((x,y),f"{v:,}",fontsize=9)
    data=document.tobytes()
    document.close()
    return data


def financial():
    return {"records": [{
        "symbol":"S63", "fiscal_year":2025,
        "metrics":{
            "revenue":{"2025":{"value":12346426}},
            "operating_profit":{"2025":{"value":843116}},
            "attributable_profit":{"2025":{"value":462770}},
        }
    }]}


class TestV40(unittest.TestCase):
    def test_2025_full_year_reported(self):
        values=from_pdf(pdf_fixture())
        self.assertEqual(values["revenue"]["value"],12346426)
        self.assertEqual(values["revenue"]["prior_year"],11275659)
        self.assertEqual(values["attributable_profit"]["value"],462770)
        self.assertEqual(values["operating_profit"]["value"],843116)

    def test_three_checks(self):
        out=compare(financial(),pdf_fixture())
        self.assertIsNone(out["error"])
        self.assertEqual(len(out["checks"]),3)
        self.assertEqual(sum(x["status"]=="MATCH_LIVE_SECOND_ISSUER_DOCUMENT" for x in out["checks"]),3)
        self.assertFalse(out["investment_ranking_eligible"])

    def test_detects_mismatch(self):
        data=financial()
        data["records"][0]["metrics"]["revenue"]["2025"]["value"]=999
        out=compare(data,pdf_fixture())
        status={c["metric"]:c["status"] for c in out["checks"]}
        self.assertEqual(status["revenue"],"MISMATCH")
        self.assertEqual(status["attributable_profit"],"MATCH_LIVE_SECOND_ISSUER_DOCUMENT")

    def test_blocks_bop(self):
        out=compare(financial(),pdf_fixture(bop_on_second=True))
        self.assertIsNotNone(out["error"])
        self.assertFalse(out["checks"])

    def test_blocks_missing_header(self):
        self.assertIsNotNone(compare(financial(),pdf_fixture(bad_header=True))["error"])

    def test_blocks_missing_revenue(self):
        self.assertIsNotNone(compare(financial(),pdf_fixture(missing=True))["error"])

    def test_fails_closed_on_bad_pdf(self):
        out=compare(financial(),b"not pdf")
        self.assertIsNotNone(out["error"])
        self.assertFalse(out["checks"])

    def test_join_does_not_duplicate(self):
        original={"records":[{"symbol":"G13","checks":[]},{"symbol":"S63","checks":[]}]}
        checked=compare(financial(),pdf_fixture())
        result=join(original,checked)
        self.assertEqual([r["symbol"] for r in result["records"]],["G13","S63"])
        self.assertEqual(result["ranking_eligible_count"],0)


if __name__ == "__main__":
    unittest.main()
