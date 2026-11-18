from datetime import date
from decimal import Decimal
import unittest

from jpx_adjust_monthly_history import analyze
import pymupdf

from jpx_share_basis import ShareEvent, read_monthly_rights


class AdjustMonthlyHistoryTest(unittest.TestCase):
    def test_archive_report_parses_a_short_split_label(self):
        with pymupdf.open() as document:
            page = document.new_page(width=700)
            page.insert_text((40, 30), "2023年6月", fontname="japan", fontsize=10)
            cells = ((90, "9432"), (140, "NTT"), (270, "2023.06.29"), (390, "2023.06.30"),
                     (520, "1:25"), (580, "分割"))
            for x, label in cells:
                page.insert_text((x, 120), label, fontname="japan", fontsize=10)
            month, events = read_monthly_rights(document.tobytes())
        self.assertEqual(month, date(2023, 6, 1))
        self.assertEqual(events["9432"], {ShareEvent(
            date(2023, 6, 29), date(2023, 6, 30), Decimal(1), Decimal(25), "分割"
        )})

    def test_compounds_relevant_splits_and_keeps_the_ex_date_close(self):
        first, split, last = (date(2026, month, 27) for month in (5, 6, 7))
        points = [(first, Decimal("400")), (split, Decimal("200")), (last, Decimal("110"))]
        coverage = {day.replace(day=1) for day, _ in points}
        events = [
            ShareEvent(split, split, Decimal(1), Decimal(2), "分割"),
            ShareEvent(last, last, Decimal(1), Decimal(2), "分割"),
            ShareEvent(date(2026, 8, 1), date(2026, 8, 1), Decimal(1), Decimal(10), "分割"),
        ]
        result = analyze(points, coverage, events, include_prices=True)
        self.assertEqual([Decimal(row["close"]) for row in result["points"]], [100, 100, 110])
        self.assertEqual(result["splits_or_consolidations"], 2)
        self.assertEqual(result["range_position"], "1.0000")
        self.assertNotIn("range_low", result)
        private = analyze(points, coverage, events, include_range=True)
        self.assertEqual(Decimal(private["range_low"]), 100)
        self.assertEqual(Decimal(private["range_high"]), 110)
        self.assertNotIn("points", private)

    def test_refuses_gaps_and_other_share_changes(self):
        first, last = date(2026, 5, 29), date(2026, 6, 30)
        points = [(first, Decimal(100)), (last, Decimal(105))]
        coverage = {day.replace(day=1) for day, _ in points}
        result = analyze(points, {first.replace(day=1)}, [])
        self.assertEqual(result["missing_months"], ("2026-06",))
        event = ShareEvent(last, last, Decimal(1), Decimal(1), "無償割当て")
        self.assertEqual(analyze(points, coverage, [event])["status"], "other_share_change")
