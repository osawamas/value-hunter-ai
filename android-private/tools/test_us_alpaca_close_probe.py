from datetime import date
import unittest

from us_alpaca_close_probe import audit, collect
from unittest.mock import patch


class AlpacaCloseProbeTest(unittest.TestCase):
    def test_checks_both_symbols_and_rejects_another_session(self):
        def fetch(*_):
            bar = {"t": "2026-11-27T05:00:00Z", "c": 100}
            return {"bars": {"AAPL": [bar], "IBM": [bar]}}

        self.assertEqual(audit(date(2026, 11, 27), "key", "secret", fetch)["verified"], 2)
        self.assertEqual(audit(date(2026, 11, 26), "key", "secret", fetch)["status"], "response_unverified")

    def test_skips_without_both_keys(self):
        self.assertEqual(audit(date(2026, 11, 27), "key", "")["status"], "key_unconfigured")

    def test_bulk_keeps_verified_batches_and_full_scope_on_later_failure(self):
        day = date(2026, 11, 27)
        symbols = [f"S{i:03}" for i in range(101)]

        def fetch(start, end, batch, adjustment, limit, key, secret):
            self.assertEqual((start, end, adjustment), (day, day, "raw"))
            if batch == ["S100"]:
                return {"bars": {"OUTSIDE": []}}
            return {"bars": {"S000": [{"t": "2026-11-27T05:00:00Z", "c": 100}]}}

        with patch("us_alpaca_close_probe.time.sleep"):
            summary, rows = collect(day, symbols, "key", "secret", fetch)
        self.assertEqual((summary["scope"], summary["queried"], summary["closes"]), (101, 100, 1))
        self.assertEqual(rows, [{"symbol": "S000", "close_usd": "100"}])
