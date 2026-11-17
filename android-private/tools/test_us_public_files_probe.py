from datetime import date, datetime
import unittest

from us_public_files_probe import coverage, read_directory

DAY = date(2026, 11, 16)
NASDAQ = (
    b"Symbol|Security Name|Test Issue|ETF|NextShares\r\n"
    b"AAPL|Apple Inc. - Common Stock|N|N|N\r\n"
    b"TEST|Test Issue|Y|N|N\r\n"
    b"AETF|An ETF|N|Y|N\r\n"
    b"NXT|A NextShares listing|N|N|Y\r\n"
    b"File Creation Time: 1117202606:00||||\r\n"
)


class PublicFilesTest(unittest.TestCase):
    def test_listing_scope_and_creation(self):
        stamp, rows = read_directory(NASDAQ, nasdaq=True)
        self.assertEqual(datetime(2026, 11, 17, 6), stamp)
        self.assertEqual({"AAPL": ("Nasdaq", "common_or_ordinary_label")}, rows)

        other = (
            b"ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
            b"BRK.B|Berkshire Class B Common Stock|N|N|N\n"
            b"AA.W|Warrants for common stock|N|N|N\n"
            b"AA|Issuer name only|N|N|N\n"
            b"File Creation Time: 1117202606:00||||\n"
        )
        _, rows = read_directory(other, nasdaq=False)
        self.assertEqual(("NYSE", "common_or_ordinary_label"), rows["BRK.B"])
        self.assertEqual(("NYSE", "other_security"), rows["AA.W"])
        self.assertEqual(("NYSE", "unclassified"), rows["AA"])

    def test_incomplete_or_duplicate_listing_is_rejected(self):
        with self.assertRaises(ValueError):
            read_directory(NASDAQ.split(b"File Creation")[0], nasdaq=True)
        with self.assertRaises(ValueError):
            read_directory(NASDAQ.replace(b"TEST|Test Issue|Y", b"AAPL|Common Stock|N"), nasdaq=True)

    def test_coverage_keeps_unclassified_and_unmatched_separate(self):
        listings = {"AAPL": ("Nasdaq", "common_or_ordinary_label"),
                    "MSFT": ("Nasdaq", "common_or_ordinary_label"),
                    "AA": ("NYSE", "unclassified")}
        result = coverage(DAY, listings, [self.bar("AAPL"), self.bar("ZZZZ"), self.bar("AA", float("nan"))])
        self.assertEqual(50.0, result["groups"]["common_or_ordinary_label"]["percent"])
        self.assertEqual(0, result["groups"]["unclassified"]["with_close"])
        self.assertEqual(1, result["unmatched_price_tickers"])

    def test_wrong_session_or_duplicate_bar_is_rejected(self):
        listings = {"AAPL": ("Nasdaq", "common_or_ordinary_label")}
        for rows in ([self.bar("AAPL")] * 2, [dict(self.bar("AAPL"), date=date(2026, 11, 13))],
                     [dict(self.bar("AAPL"), asset_type="ETF")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                coverage(DAY, listings, rows)

    @staticmethod
    def bar(symbol, close=10):
        return {"symbol": symbol, "date": DAY, "asset_type": "Stock", "close": close}


if __name__ == "__main__":
    unittest.main()
