from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from us_nyse_taq_probe import benchmark, read_nyse_sample


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
