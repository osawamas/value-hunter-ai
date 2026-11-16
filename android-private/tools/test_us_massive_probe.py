from datetime import date
import unittest

from us_massive_probe import ProbeError, coverage, listed_common_stocks


class MassiveCoverageTest(unittest.TestCase):
    day = date(2020, 10, 14)
    timestamp = 1602705600000  # Massive's grouped-daily example, 16:00 New York.

    def test_counts_only_listed_common_stocks_with_a_valid_close(self):
        payload = {"adjusted": False, "resultsCount": 3, "results": [
            {"T": "A", "c": 2, "t": self.timestamp},
            {"T": "ETF", "c": 3, "t": self.timestamp},
            {"T": "B", "c": float("nan"), "t": self.timestamp},
        ]}
        result = coverage(self.day, payload, {"A", "B", "C"})
        self.assertEqual(result["common_stocks_with_close"], 1)
        self.assertEqual(result["common_stocks_without_close"], 2)
        self.assertEqual(result["invalid_or_otc_rows"], 1)

    def test_rejects_a_bar_from_another_eastern_trading_date(self):
        payload = {"adjusted": False, "resultsCount": 1, "results": [
            {"T": "A", "c": 2, "t": self.timestamp - 86_400_000},
        ]}
        with self.assertRaisesRegex(ProbeError, "different New York date"):
            coverage(self.day, payload, {"A"})

    def test_rejects_a_duplicate_bar(self):
        row = {"T": "A", "c": 2, "t": self.timestamp}
        with self.assertRaisesRegex(ProbeError, "Duplicate symbol"):
            coverage(self.day, {"adjusted": False, "resultsCount": 2, "results": [row, row]}, {"A"})

    def test_follows_ticker_cursor_and_preserves_exact_symbols(self):
        base = {"type": "CS", "active": True, "locale": "us", "market": "stocks"}
        pages = iter([
            {"results": [dict(base, ticker="A")],
             "next_url": "https://api.massive.com/v3/reference/tickers?cursor=page2"},
            {"results": [dict(base, ticker="B.A")]},
        ])
        paths = []

        def get(path):
            paths.append(path)
            return next(pages)

        self.assertEqual(listed_common_stocks(get, self.day), {"A", "B.A"})
        self.assertIn("date=2020-10-14", paths[0])
        self.assertEqual(paths[1], "/v3/reference/tickers?cursor=page2")

    def test_rejects_pagination_to_another_host(self):
        def get(_):
            return {"results": [], "next_url": "https://example.org/v3/reference/tickers?cursor=page2"}

        with self.assertRaisesRegex(ProbeError, "pagination URL"):
            listed_common_stocks(get, self.day)


if __name__ == "__main__":
    unittest.main()
