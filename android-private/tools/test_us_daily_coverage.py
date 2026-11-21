from datetime import date, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from us_daily_coverage import archive_dia_holdings, compare_missing_symbols, compare_previous_report, compare_session, dia_for_session, run_cycle


class DailyCoverageTest(unittest.TestCase):
    def test_current_missing_symbols_must_be_unique_and_canonical(self):
        previous = {"missing_close_symbols_by_exchange": {"NYSE": ["AAA", "BBB"]}}
        current = {"missing_close_symbols_by_exchange": {"NYSE": ["AAA", "AAA"]}}
        self.assertEqual({}, compare_missing_symbols(previous, current, "NYSE", 2, 2))
        current["missing_close_symbols_by_exchange"]["NYSE"] = ["AAA", "bad symbol"]
        self.assertEqual({}, compare_missing_symbols(previous, current, "NYSE", 2, 2))
        current["missing_close_symbols_by_exchange"]["NYSE"] = ["AAA", "CCC"]
        self.assertEqual(
            {"recovered_symbols": ["BBB"], "newly_missing_symbols": ["CCC"]},
            compare_missing_symbols(previous, current, "NYSE", 2, 2),
        )

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
        sync.return_value = "updated"
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
            self.assertEqual("updated", report["dolt_sync"])
            self.assertNotIn("AAPL", json.dumps(report))
            self.assertEqual({"NYSE": ["BIO.B"], "Nasdaq": []}, report["missing_close_symbols_by_exchange"])
            self.assertEqual("observed_unverified", report["coverage_status"])
            self.assertEqual({"nasdaqlisted.txt", "otherlisted.txt"}, report["directory_sha256"].keys())
            again = run_cycle(root, root / "stocks", now, calendar)
            self.assertEqual("refreshed", again["sessions"][1]["status"])
            counts = again["sessions"][1]["common_or_ordinary_label_by_exchange"]
            self.assertEqual(1, counts["NYSE"]["with_close"])
            gained = again["sessions"][1]["previous_observation"]["markets"]["NYSE"]
            self.assertEqual(1, gained["change_in_with_close"])
            self.assertEqual(["BIO.B"], gained["recovered_symbols"])
            later = run_cycle(root, root / "stocks", now, calendar)
            drop = later["sessions"][1]["previous_observation"]["markets"]["NYSE"]
            self.assertEqual(-1, drop["change_in_with_close"])
            self.assertEqual(["BIO.B"], drop["newly_missing_symbols"])
            last_report = report_path.read_bytes()
            self.assertEqual(drop, json.loads(last_report)["previous_observation"]["markets"]["NYSE"])
            empty = run_cycle(root, root / "stocks", now, calendar)
            self.assertTrue(empty["sessions"][1]["previous_report_retained"])
            self.assertEqual(last_report, report_path.read_bytes())
            self.assertEqual("outside_capture_window",
                             run_cycle(root, root / "stocks", now.replace(hour=13), calendar)["status"])
            self.assertEqual(4, sync.call_count)


    @patch("us_daily_coverage.sync")
    @patch("us_daily_coverage.dolt_rows")
    def test_stale_dolt_cache_does_not_overwrite_saved_coverage(self, prices, sync):
        eastern = ZoneInfo("America/New_York")
        now = datetime(2026, 11, 17, 12, 45, tzinfo=eastern)
        calendar = Mock()
        calendar.is_session.return_value = True
        calendar.sessions_in_range.return_value = [datetime(2026, 11, 16)]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "2026-11-16"
            snapshot.mkdir()
            (snapshot / "nasdaqlisted.txt").write_text(
                "Symbol|Security Name|Test Issue|ETF|NextShares\n"
                "AAPL|Common Stock|N|N|N\nFile Creation Time: 1116202612:00||||\n"
            )
            (snapshot / "otherlisted.txt").write_text(
                "ACT Symbol|Security Name|Exchange|Test Issue|ETF\n"
                "BIO.B|Common Stock|N|N|N\nFile Creation Time: 1116202612:00||||\n"
            )
            current = root / "2026-11-17"
            current.mkdir()
            (current / "nasdaqlisted.txt").write_text(
                "Symbol|Security Name|Test Issue|ETF|NextShares\n"
                "AAPL|Common Stock|N|N|N\nFile Creation Time: 1117202612:00||||\n"
            )
            (current / "otherlisted.txt").write_text(
                "ACT Symbol|Security Name|Exchange|Test Issue|ETF\n"
                "BIO.B|Common Stock|N|N|N\nFile Creation Time: 1117202612:00||||\n"
            )
            report = snapshot / "dolt-coverage.json"
            report.write_bytes(b'{"verified_previous": true}\n')
            for failure in ("cached_after_timeout", "cached_after_rate_limit", "cached_after_os_error"):
                with self.subTest(failure=failure):
                    sync.return_value = failure
                    outcome = run_cycle(root, root / "stocks", now, calendar)
                    self.assertEqual("dolt_stale_cache", outcome["status"])
                    self.assertEqual(["2026-11-16"], outcome["pending_sessions"])
                    self.assertEqual([], outcome["sessions"])
                    self.assertEqual(b'{"verified_previous": true}\n', report.read_bytes())
            prices.assert_not_called()

    def test_reports_symbol_changes_even_with_unchanged_market_totals(self):
        report = {"trading_date": "2026-11-16", "sample_price_basis": "Dolt",
                  "directory_observed_at": {"otherlisted.txt": "2026-11-16T11:00:00"},
                  "directory_sha256": {"otherlisted.txt": "same"},
                  "common_or_ordinary_label_by_exchange": {
                      "NYSE": {"listed": 2, "with_close": 1, "without_close": 1},
                  },
                  "missing_close_symbols_by_exchange": {"NYSE": ["AAA"]}}
        previous = dict(report, missing_close_symbols_by_exchange={"NYSE": ["BBB"]})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(previous))
            change = compare_previous_report(path, report)["markets"]["NYSE"]
            self.assertEqual(0, change["change_in_with_close"])
            self.assertEqual(["BBB"], change["recovered_symbols"])
            self.assertEqual(["AAA"], change["newly_missing_symbols"])
            previous.pop("missing_close_symbols_by_exchange")
            path.write_text(json.dumps(previous))
            legacy = compare_previous_report(path, report)["markets"]["NYSE"]
            self.assertEqual(0, legacy["change_in_with_close"])
            self.assertNotIn("recovered_symbols", legacy)

    def test_does_not_compare_incompatible_previous_directory(self):
        observed = {"trading_date": "2026-11-16", "sample_price_basis": "Dolt",
                    "directory_observed_at": {"otherlisted.txt": "2026-11-16T11:00:00"}}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(dict(observed, directory_observed_at={})))
            self.assertEqual("different_report_basis", compare_previous_report(path, observed)["status"])
            path.write_text(json.dumps(dict(observed, directory_sha256={"otherlisted.txt": "different"})))
            self.assertEqual("different_report_basis", compare_previous_report(path, observed)["status"])
            # A legacy report without hashes must not claim a recovered ticker
            # against a newly hashed listing directory, even at the same timestamp.
            hashed = dict(observed, directory_sha256={"otherlisted.txt": "current"})
            path.write_text(json.dumps(observed))
            self.assertEqual("different_report_basis", compare_previous_report(path, hashed)["status"])
            path.write_text(json.dumps(hashed))
            self.assertEqual("different_report_basis", compare_previous_report(path, observed)["status"])
            # Two legacy reports without hashes are also not a verified pair.
            legacy_with_counts = dict(observed, common_or_ordinary_label_by_exchange={
                "NYSE": {"listed": 1, "with_close": 1, "without_close": 0}})
            path.write_text(json.dumps(legacy_with_counts))
            self.assertEqual("different_report_basis",
                             compare_previous_report(path, legacy_with_counts)["status"])
            empty_hash = dict(legacy_with_counts, directory_sha256={})
            path.write_text(json.dumps(empty_hash))
            self.assertEqual("different_report_basis",
                             compare_previous_report(path, empty_hash)["status"])
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


    @patch("us_daily_coverage.parquet_rows")
    @patch("us_daily_coverage.fetch")
    @patch("us_daily_coverage.dolt_rows")
    @patch("us_daily_coverage.load_listing_directories")
    def test_optional_second_source_reports_extra_tickers_without_changing_primary(self, directories, prices, fetch, read):
        day = date(2026, 11, 16)
        now = datetime(2026, 11, 17, 12, tzinfo=ZoneInfo("America/New_York"))
        observed = {name: "2026-11-16T12:00:00" for name in ("nasdaqlisted.txt", "otherlisted.txt")}
        listings = {symbol: ("Nasdaq", "common_or_ordinary_label") for symbol in ("AAPL", "AAA", "BBB")}
        directories.return_value = (observed, listings, {})
        aapl = {"symbol": "AAPL", "asset_type": "Stock", "date": day, "close": 50.0}
        prices.return_value = [aapl]
        fetch.return_value = b"sample"
        read.return_value = [aapl, dict(aapl, symbol="AAA")]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            result = compare_session(day, root, root / "stocks", "updated", now, compare_marketparquet=True)
            self.assertEqual({"NYSE": 0, "Nasdaq": 1}, result["marketparquet_only_by_exchange"])
            report = json.loads(Path(result["report"]).read_text())
            comparison = report["dolt_marketparquet_comparison"]["Nasdaq"]
            self.assertEqual(["AAA"], comparison["only_marketparquet_symbols"])
            self.assertEqual(["BBB"], comparison["missing_from_both_symbols"])
            self.assertEqual(["AAA", "BBB"], report["missing_close_symbols_by_exchange"]["Nasdaq"])
            read.return_value = [dict(aapl, date=date(2026, 11, 15))]
            wrong_date = compare_session(day, root, root / "stocks", "updated", now, compare_marketparquet=True)
            self.assertEqual("unavailable", wrong_date["marketparquet_reference"]["status"])
            self.assertEqual(1, wrong_date["common_or_ordinary_label_by_exchange"]["Nasdaq"]["with_close"])
            self.assertNotIn("dolt_marketparquet_comparison", json.loads(Path(wrong_date["report"]).read_text()))


if __name__ == "__main__":
    unittest.main()
