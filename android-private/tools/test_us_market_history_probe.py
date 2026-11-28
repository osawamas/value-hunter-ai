import json
from datetime import date
from decimal import Decimal
import unittest

from us_market_history_probe import dated_regular_closes


class MarketHistoryProbeTest(unittest.TestCase):
    def test_reads_new_york_open_across_dst_and_rejects_conflicts(self):
        first = {"timestamp": "2026-10-30T13:30:00Z", "is_gap": False, "symbol": "AAPL", "close": 150.25}
        second = dict(first, timestamp="2026-11-02T14:30:00Z", close=151)
        body = "\n".join(map(json.dumps, [first, second])).encode()
        self.assertEqual(dated_regular_closes(body, "AAPL"),
                         {date(2026, 10, 30): Decimal("150.25"), date(2026, 11, 2): Decimal("151")})
        with self.assertRaises(ValueError):
            dated_regular_closes(body + b"\n" + json.dumps(first).encode(), "AAPL")
        with self.assertRaises(ValueError):
            dated_regular_closes(json.dumps(dict(second, timestamp="2026-11-02T13:30:00Z")).encode(), "AAPL")
