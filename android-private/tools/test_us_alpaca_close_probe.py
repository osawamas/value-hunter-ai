from datetime import date, timedelta
import unittest

from us_alpaca_close_probe import audit, collect, replay_history, split_audit
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


    def test_replay_excludes_unavailable_forward_windows(self):
        first = date(2020, 1, 1)
        rows = {(symbol, first + timedelta(days=n)): (100 + n if symbol == "AAPL" else 100)
                for symbol in ("AAPL", "IBM") for n in range(273)}
        self.assertEqual(replay_history(rows)["test_windows"], 0)
        for symbol in ("AAPL", "IBM"):
            rows[symbol, first + timedelta(days=273)] = 373 if symbol == "AAPL" else 100
        result = replay_history(rows)
        self.assertEqual((result["qualified_signals"], result["positive_forward_windows"], result["relative_wins"]),
                         (1, 1, 1))

    def test_split_audit_keeps_ex_dates_in_scope_and_rejects_bad_pagination(self):
        def fetch(path, params, *_):
            self.assertEqual(path, "/v1/corporate-actions")
            if "page_token" not in params:
                return {"corporate_actions": {"forward_splits": [
                    {"id": "first", "symbol": "AAPL", "ex_date": "2026-10-02"},
                    {"id": "future", "symbol": "AAPL", "ex_date": "2026-12-02"}]},
                        "next_page_token": "second-page"}
            return {"corporate_actions": {"reverse_splits": [
                {"id": "last", "symbol": "AAPL", "ex_date": "2026-11-02"},
                {"id": "other", "symbol": "IBM", "ex_date": "2026-11-03"}]},
                    "next_page_token": None}

        with patch("us_alpaca_close_probe.time.sleep"):
            report, splits = split_audit(date(2026, 11, 27), {"AAPL"}, "key", "secret", fetch)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(splits, {"AAPL": "2026-11-02"})
