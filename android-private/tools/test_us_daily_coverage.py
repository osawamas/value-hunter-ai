from datetime import date, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from us_daily_coverage import archive_dia_holdings, compare_previous_report, compare_session, dia_for_session, run_cycle


class DailyCoverageTest(unittest.TestCase):
    @patch("us_daily_coverage.sync")
    @patch("us_daily_coverage.dolt_rows")
    def test_rechecks_saved_reports_and_retains_them_when_dolt_has_no_data(self, prices, sync):
        eastern = ZoneInfo("America/New_York")
        now = datetime(2026, 11, 17, 12, 45, tzinfo=eastern)
        calendar = Mock()
        calendar.is_session.return_value = True
        calendar.sessions_in_range.return_value = [datetime(2026, 11, 13), datetime(2026, 11, 16)]
        day = date(2026, 11, 16)
        aapl = {"symbol": "AAPL", "asset_type": "Stock", "date": day, "close": 50.0}
        bio = dict(aapl, symbol="BIO.B")
        prices.side_effect = [[], [aapl], [], [aapl, bio], [], [aapl], [], []]
        sync.return_value = "cached_after_rate_limit"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for stamp in ("2026-11-13", "2026-11-16", "2026-11-17"):
                current = root / stamp
                current.mkdir()
                us_date = date.fromisoformat(stamp).strftime("%m%d%Y")
                (current / "nasdaqlisted.txt").write_text(
                    "Symbol|Security Name|Test Issue|ETF|NextShares\n"
                    f"AAPL|Common Stock|N|N|N\nFile Creation Time: {us_date}12:00||||\n"
                )
                (current / "otherlisted.txt").write_text(
                    "ACT Symbol|Security Name|Exchange|Test Issue|ETF\n"
                    f"BIO.B|Common Stock|N|N|N\nFile Creation Time: {us_date}12:00||||\n"
                )
            result = run_cycle(root, root / "stocks", now, calendar)
            self.assertEqual("already_saved", result["capture"])
            self.assertEqual(["no_dolt_closes_for_session", "compared"],
                             [row["status"] for row in result["sessions"]])
            self.assertFalse((root / "2026-11-13/dolt-coverage.json").exists())
            report_path = root / "2026-11-16/dolt-coverage.json"
            report = json.loads(report_path.read_text())
            self.assertEqual("same_day_directory_unverified", report["listing_snapshot_assessment"]["status"])
            self.assertEqual("cached_after_rate_limit", report["dolt_sync"])
            self.assertNotIn("AAPL", json.dumps(report))
            self.assertEqual("observed_unverified", report["coverage_status"])
            self.assertEqual({"nasdaqlisted.txt", "otherlisted.txt"}, report["directory_sha256"].keys())
            again = run_cycle(root, root / "stocks", now, calendar)
            self.assertEqual("refreshed", again["sessions"][1]["status"])
            counts = again["sessions"][1]["common_or_ordinary_label_by_exchange"]
            self.assertEqual(1, counts["NYSE"]["with_close"])
            self.assertEqual(1, again["sessions"][1]["previous_observation"]["markets"]["NYSE"]["change_in_with_close"])
            later = run_cycle(root, root / "stocks", now, calendar)
            drop = later["sessions"][1]["previous_observation"]["markets"]["NYSE"]
            self.assertEqual({"previous_with_close": 1, "current_with_close": 0, "change_in_with_close": -1}, drop)
            last_report = report_path.read_bytes()
            self.assertEqual(drop, json.loads(last_report)["previous_observation"]["markets"]["NYSE"])
            empty = run_cycle(root, root / "stocks", now, calendar)
            self.assertTrue(empty["sessions"][1]["previous_report_retained"])
            self.assertEqual(last_report, report_path.read_bytes())
            self.assertEqual("outside_capture_window",
                             run_cycle(root, root / "stocks", now.replace(hour=13), calendar)["status"])
            self.assertEqual(4, sync.call_count)


    def test_does_not_compare_incompatible_previous_directory(self):
        observed = {"trading_date": "2026-11-16", "sample_price_basis": "Dolt",
                    "directory_observed_at": {"otherlisted.txt": "2026-11-16T11:00:00"}}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(dict(observed, directory_observed_at={})))
            self.assertEqual("different_report_basis", compare_previous_report(path, observed)["status"])
            path.write_text(json.dumps(dict(observed, directory_sha256={"otherlisted.txt": "different"})))
            self.assertEqual("different_report_basis", compare_previous_report(path, observed)["status"])
            path.write_text("{")
            self.assertEqual("previous_report_unreadable", compare_previous_report(path, observed)["status"])


    @patch("us_daily_coverage.load_dia")
    @patch("us_daily_coverage.fetch")
    @patch("us_daily_coverage.dolt_rows")
    @patch("us_daily_coverage.load_listing_directories")
    def test_dia_archive_uses_workbook_date_and_keeps_other_days_comparable(self, directories, prices, fetch, dia):
        day = date(2026, 11, 16)
        today = date(2026, 11, 17)
        now = datetime(2026, 11, 17, 12, tzinfo=ZoneInfo("America/New_York"))
        observed = {name: "2026-11-16T12:00:00" for name in ("nasdaqlisted.txt", "otherlisted.txt")}
        directories.return_value = (observed, {"AAPL": ("Nasdaq", "common_or_ordinary_label")}, {})
        prices.return_value = [{"symbol": "AAPL", "asset_type": "Stock", "date": day, "close": 50.0}]
        fetch.return_value = b"original workbook"
        dia.return_value = (day, {"AAPL"} | {f"TEST{i}" for i in range(29)})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dia_directory = root / "dia-holdings"
            self.assertEqual({"status": "saved", "as_of": day.isoformat()}, archive_dia_holdings(dia_directory, today))
            self.assertEqual("already_saved", archive_dia_holdings(dia_directory, today)["status"])
            self.assertEqual((None, "no_same_date_holdings"), dia_for_session(dia_directory, today))
            match = compare_session(day, root, root / "stocks", "updated", now, dia_directory=dia_directory)
            self.assertEqual(30, match["dia_holdings_comparison"]["symbols"])
            self.assertEqual(1, match["dia_holdings_comparison"]["with_close"])
            dia.return_value = (today, {"AAPL"})
            mismatch = compare_session(day, root, root / "stocks", "updated", now, dia_directory=dia_directory)
            self.assertEqual("holdings_date_mismatch", mismatch["dia_holdings_status"])
            self.assertNotIn("dia_holdings_comparison", mismatch)
            self.assertEqual(1, mismatch["common_or_ordinary_label_by_exchange"]["Nasdaq"]["with_close"])


if __name__ == "__main__":
    unittest.main()
