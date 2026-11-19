from datetime import date
from decimal import Decimal
import unittest

from us_nasdaq_close_probe import parse


class NasdaqHistoricalCloseTest(unittest.TestCase):
    def setUp(self):
        self.days = {date(2026, 11, 16), date(2026, 11, 17)}
        self.rows = [{"date": "11/17/2026", "close": "$11.2500"},
                     {"date": "11/16/2026", "close": "$12.5000"}]
        self.data = {"symbol": "TEST", "totalRecords": 2, "tradesTable": {"rows": self.rows}}
        self.payload = {"status": {"rCode": 200}, "data": self.data}

    def test_reads_only_the_requested_symbol_and_dates(self):
        closes = parse(self.payload, "TEST", self.days)
        self.assertEqual(set(closes), self.days)
        self.assertEqual(closes[date(2026, 11, 17)], Decimal("11.2500"))
        with self.assertRaises(ValueError):
            parse(self.payload, "IBM", self.days)

    def test_rejects_duplicate_or_stale_dates(self):
        for bad_day in ("11/17/2026", "11/15/2026"):
            with self.subTest(bad_day=bad_day):
                self.rows[1]["date"] = bad_day
                with self.assertRaises(ValueError):
                    parse(self.payload, "TEST", self.days)

    def test_fails_closed_for_incomplete_output_and_accepts_explicit_empty(self):
        self.rows.pop()
        with self.assertRaises(ValueError):
            parse(self.payload, "TEST", self.days)
        self.data.update(totalRecords=0, tradesTable={"rows": None})
        self.assertEqual(parse(self.payload, "TEST", self.days), {})
