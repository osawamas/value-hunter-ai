from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from us_nyse_taq_probe import benchmark, follow_missing, read_nyse_sample


class NyseTaqProbeTest(unittest.TestCase):
    def test_dated_last_filters_carry_forward_and_other_markets(self):
        day = date(2026, 7, 1)
        rows = [f"{symbol}|000000000|1|1|1|10.10|0|{vol}|{stamp}|0|0|0|0|{exchange}"
                for symbol, vol, stamp, exchange in (
                    ("AAA", 10, "07/01/2026", "N"),
                    ("BBB", 10, "07/01/2026", "N"),
                    ("CCC", 10, "07/01/2026", "N"),
                    ("DDD", 10, "07/01/2026", "N"),
                    ("STALE", 50, "06/30/2026", "N"),
                    ("NOVOL", 0, "07/01/2026", "N"),
                    ("BRK B", 10, "07/01/2026", "N"),
                    ("AAPL", 10, "07/01/2026", "Q"),
                )]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "EQY_US_NYSE_SUM_CLOSE_20260701.txt"
            source.write_text("\n".join(rows))
            reference, checks = read_nyse_sample(source, day)
            self.assertEqual({"AAA", "BBB", "CCC", "DDD"}, reference.keys())
            self.assertEqual(1, checks["excluded_different_or_blank_trade_date"])
            self.assertEqual(1, checks["excluded_no_positive_last_or_volume"])
            with self.assertRaises(ValueError):
                read_nyse_sample(source, date(2026, 7, 2))
        result = benchmark(day, reference, [
            {"asset_type": "Stock", "date": day, "symbol": "AAA", "close": 10.11},
            {"asset_type": "Stock", "date": day, "symbol": "BBB", "close": 10.12},
            {"asset_type": "Stock", "date": day, "symbol": "DDD", "close": None},
        ])
        self.assertEqual(1, result["within_one_cent_nonexact"])
        self.assertEqual(1, result["differ_over_one_cent"])
        self.assertEqual(2, result["missing_dolt"])
        self.assertEqual({
            "no_dolt_row": ["CCC"],
            "dolt_row_without_usable_close": ["DDD"],
            "differ_over_one_cent": ["BBB"],
        }, result["exceptions"])


    @patch("us_nyse_taq_probe.dolt_csv")
    def test_missing_follow_up_keeps_not_found_and_rejects_out_of_window_data(self, query):
        day, end = date(2026, 7, 2), date(2026, 7, 10)
        query.return_value = b"symbol,first_close_date\nSECZ,2026-07-06\n"
        result = follow_missing(Path("stocks"), day, end, ["SECZ", "OTAI"])
        self.assertEqual({"SECZ": "2026-07-06"}, result["first_later_close_date_by_symbol"])
        self.assertEqual(["OTAI"], result["no_later_close_in_window"])
        self.assertIn("date > '2026-07-02'", query.call_args.args[1])
        query.return_value = b"symbol,first_close_date\nSECZ,2026-07-02\n"
        with self.assertRaises(ValueError):
            follow_missing(Path("stocks"), day, end, ["SECZ"])


    def test_share_class_option_keeps_a_b_and_unsuffixed_tickers_distinct(self):
        day = date(2026, 7, 1)
        rows = "\n".join(f"{symbol}|000000000|1|1|1|10.10|0|100|07/01/2026|0|0|0|0|N"
                         for symbol in ("BF", "BF A", "BF B", "BF PR", "BF BWI"))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "EQY_US_NYSE_SUM_CLOSE_20260701.txt"
            path.write_text(rows)
            self.assertEqual({"BF"}, read_nyse_sample(path, day)[0].keys())
            reference, checks = read_nyse_sample(path, day, include_share_classes=True)
        self.assertEqual({"BF", "BF.A", "BF.B"}, reference.keys())
        self.assertEqual(2, checks["included_share_class_rows"])
        bars = [{"asset_type": "Stock", "date": day, "symbol": symbol, "close": 10.10}
                for symbol in ("BF", "BF.A")]
        result = benchmark(day, reference, bars)
        self.assertEqual(["BF.B"], result["share_class_scope"]["missing_dolt_symbols"])
