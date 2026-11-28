from datetime import date, timedelta
from decimal import Decimal
import sqlite3
import unittest

from us_alpaca_history import DownloadBudget, collect, pages, schema, update_batch, valuation_history


class HistoryCollectionTest(unittest.TestCase):
    def test_resumes_at_the_first_uncommitted_batch(self):
        day = date(2026, 11, 27)
        with sqlite3.connect(":memory:") as db:
            symbols = [f"S{i:02}" for i in range(25)]
            calls = []

            def fetch(start, end, batch, token):
                calls.append(batch)
                if len(calls) == 2:
                    raise DownloadBudget()
                return {"bars": {}, "next_page_token": None}

            first, _ = collect(db, symbols, day, fetch)
            self.assertEqual(first["request_complete"], 23)
            self.assertEqual(first["symbols_with_bars"], 0)
            second, _ = collect(db, symbols, day, fetch)
            self.assertEqual(second["request_complete"], 25)
            self.assertEqual(calls[-1], ["S23", "S24"])

    def test_rebuilds_on_rebased_overlap(self):
        day = date(2026, 11, 27)
        previous = date(2026, 11, 26)
        old_start = date(2021, 11, 27)
        with sqlite3.connect(":memory:") as db:
            schema(db)
            db.execute("INSERT INTO close VALUES ('AAPL','2026-11-25','200')")
            calls = []

            def fetch(start, end, batch, token):
                calls.append(start)
                return {"bars": {"AAPL": [{"t": "2026-11-25T05:00:00Z", "c": 100}]},
                        "next_page_token": None}

            update_batch(db, ["AAPL"], old_start, day, previous, fetch)
            self.assertEqual(calls[-1], old_start)
            self.assertEqual(len(calls), 2)
            self.assertEqual(Decimal(db.execute("SELECT value FROM close").fetchone()[0]), Decimal("100"))

    def test_rejects_repeated_pagination_tokens(self):
        day = date(2026, 11, 27)
        with self.assertRaises(ValueError):
            pages(day, day, ["AAPL"], lambda *_: {"bars": {}, "next_page_token": "repeat"})

    def test_selects_one_year_for_a_recent_listing_but_rejects_gaps(self):
        day = date(2026, 11, 27)
        days = sorted(day - timedelta(days=n) for n in range(366)
                      if (day - timedelta(days=n)).weekday() < 5)
        rows = {("IWV", session): Decimal("100") for session in days}
        rows.update({("NEW", session): Decimal("90") for session in days})
        self.assertEqual(valuation_history(rows, ["NEW"], "IWV", day, adaptive=True)["eligible_horizons"],
                         {"NEW": 1})
        for session in days[20:33]:
            del rows["NEW", session]
        self.assertEqual(valuation_history(rows, ["NEW"], "IWV", day, adaptive=True)["eligible_horizons"], {})
