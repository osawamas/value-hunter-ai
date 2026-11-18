from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from us_monitor_ledger import reference_screen
from us_monitor_sync import exclusive, get_splits, refresh_companyfacts

DAY = date(2026, 11, 17)


class MonitorSyncTest(TestCase):
    def test_rejects_truncated_split_response(self):
        manifest = {"query_execution_status": "Success",
                    "rows": [{"revision": "a" * 32, "n": "2"}]}
        rows = {"query_execution_status": "Success", "rows": []}
        with patch("us_monitor_sync.fetch", side_effect=[json.dumps(manifest), json.dumps(rows)]):
            with self.assertRaisesRegex(ValueError, "Incomplete split history"):
                get_splits(DAY)

    def test_keeps_existing_archive_if_replacement_is_incomplete(self):
        with TemporaryDirectory() as workspace:
            cache = Path(workspace) / "companyfacts.zip"
            stage = Path(workspace) / "download.zip"
            cache.write_bytes(b"previous")
            with ZipFile(stage, "w") as archive:
                archive.writestr("CIK0000320193.json", "{}")
            with patch("us_monitor_sync.subprocess.run") as curl:
                curl.return_value.stdout = "200"
                with self.assertRaisesRegex(ValueError, "Incomplete SEC"):
                    refresh_companyfacts(cache, stage, "test contact")
                self.assertEqual(cache.read_bytes(), b"previous")
                curl.return_value.stdout = "304"
                refresh_companyfacts(cache, stage, "test contact")
                self.assertEqual(cache.read_bytes(), b"previous")

    def test_lock_prevents_concurrent_sync(self):
        with TemporaryDirectory() as workspace:
            with exclusive(Path(workspace)) as first:
                with exclusive(Path(workspace)) as second:
                    self.assertTrue(first)
                    self.assertFalse(second)

    def test_reference_rows_exclude_unverified_prices_and_share_bases(self):
        base = {"cik": 1, "exchange": "NYSE", "shares": 100, "profit": 200,
                "equity": 1000, "share_date": "2026-11-10"}
        rows = [dict(base, symbol="OK"), dict(base, symbol="SPLT"),
                dict(base, symbol="LOSS", profit=-1), dict(base, symbol="NO_PRICE")]
        splits = {"query_execution_status": "Success",
                  "rows": [{"symbol": "SPLT", "split_date": "2026-11-10"}]}
        fx = [{"base": "USD", "quote": "JPY", "date": str(DAY), "rate": 150}]
        summary, observations = reference_screen(rows, {"OK": 5, "SPLT": 5, "LOSS": 5}, DAY, fx, splits)
        self.assertEqual(summary["exchanges"]["NYSE"],
                         {"priority": 1, "hold_split": 1, "hold_nonpositive_profit_or_equity": 1})
        self.assertEqual(observations, [
            {"symbol": "OK", "exchange": "NYSE", "cik": 1, "status": "priority", "quantity": 100},
        ])
