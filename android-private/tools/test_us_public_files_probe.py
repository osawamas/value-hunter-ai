from datetime import date, datetime
import json
import unittest

from us_public_files_probe import coverage, read_directory, read_sec_directory

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

    def test_sec_join_checks_exchange_and_counts_share_classes(self):
        kind = "common_or_ordinary_label"
        listings = {
            "BRK.A": ("NYSE", kind), "BRK.B": ("NYSE", kind),
            "SAME": ("Nasdaq", kind), "DIFF": ("Nasdaq", kind),
            "NONE": ("Nasdaq", kind), "MISS": ("NYSE American", kind),
        }
        sec = self.sec_rows([
            [1, "Issuer A", "BRK-A", "NYSE"], [1, "Issuer A", "BRK-B", "NYSE"],
            [2, "Issuer B", "SAME", "Nasdaq"], [3, "Issuer C", "SAME", "Nasdaq"],
            [4, "Issuer D", "DIFF", "OTC"], [5, "Issuer E", "MISS", "NYSE"],
        ])
        result = coverage(DAY, listings, [self.bar(ticker) for ticker in listings if ticker != "MISS"], sec)
        join = result["common_or_ordinary_label_sec_join"]
        self.assertEqual(3, join["listed_with_sec_issuer"])
        self.assertEqual(2, join["listed_with_close_and_sec_issuer"])
        self.assertEqual(2, join["with_both_sharing_issuer_with_another_listed_class"])
        self.assertEqual(3, join["with_close_missing_sec_issuer"])
        self.assertEqual(1, join["with_sec_issuer_missing_close"])
        self.assertEqual({"ambiguous_sec_issuer": 1, "sec_exchange_unconfirmed": 1, "no_sec_ticker": 1},
                         join["unlinked"])

    def test_sec_alias_cannot_steal_another_listing(self):
        kind = "common_or_ordinary_label"
        listings = {"FOO.A": ("NYSE", kind), "FOO-A": ("NYSE", kind)}
        sec = self.sec_rows([[1, "Issuer A", "FOO-A", "NYSE"]])
        result = coverage(DAY, listings, [self.bar("FOO.A")], sec)
        self.assertEqual(0, result["common_or_ordinary_label_sec_join"]["listed_with_close_and_sec_issuer"])

    def test_sec_data_must_have_valid_schema_and_issuer_id(self):
        with self.assertRaises(ValueError):
            read_sec_directory(b"{}")
        with self.assertRaises(ValueError):
            self.sec_rows([[False, "Issuer", "A", "Nasdaq"]])

    @staticmethod
    def sec_rows(rows):
        return read_sec_directory(json.dumps({"fields": ["cik", "name", "ticker", "exchange"],
                                              "data": rows}).encode())

    @staticmethod
    def bar(symbol, close=10):
        return {"symbol": symbol, "date": DAY, "asset_type": "Stock", "close": close}


if __name__ == "__main__":
    unittest.main()
