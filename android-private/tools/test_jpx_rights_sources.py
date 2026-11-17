"""Regression tests for JPX source provenance and conflicting daily editions."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
from datetime import date

from urllib.error import HTTPError

import jpx_daily_sources as daily
import jpx_rights_sources as sources


class SourceProvenanceTests(TestCase):
    def test_duplicate_daily_edition_identical_is_accepted(self):
        day = date(2026, 11, 16)
        urls = [
            "https://www.jpx.co.jp/listing/others/ex-rights/a/20261116.xls",
            "https://www.jpx.co.jp/listing/others/ex-rights/b/20261116.xls",
        ]
        with TemporaryDirectory() as temp, patch.object(sources, "download", return_value=b"same"), \
             patch.object(sources, "read_daily_rights", return_value=(day, {}, set())), \
             patch.object(sources, "workbook_notes", return_value=[]):
            results, _, _ = sources.daily_sources(urls, Path(temp))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[day.isoformat()]["sha256"], hashlib.sha256(b"same").hexdigest())

    def test_conflicting_daily_editions_fail_closed(self):
        day = date(2026, 11, 16)
        urls = [
            "https://www.jpx.co.jp/listing/others/ex-rights/a/20261116.xls",
            "https://www.jpx.co.jp/listing/others/ex-rights/b/20261116.xls",
        ]
        with TemporaryDirectory() as temp, patch.object(sources, "download", side_effect=[b"first", b"revised"]), \
             patch.object(sources, "read_daily_rights", return_value=(day, {}, set())), \
             patch.object(sources, "workbook_notes", return_value=[]):
            with self.assertRaisesRegex(ValueError, "Conflicting JPX daily workbook editions"):
                sources.daily_sources(urls, Path(temp))


class LatestDailyReportTests(TestCase):
    def test_skips_missing_report_and_weekend(self):
        today = date(2026, 11, 17)
        friday = date(2026, 11, 13)
        missing = HTTPError("url", 404, "not found", {}, None)
        with TemporaryDirectory() as temp:
            path = Path(temp) / "latest.pdf"
            with patch.object(daily, "download", side_effect=[missing, b"friday"]) as download, \
                 patch.object(daily, "trading_date", return_value=friday):
                day, url = daily.latest_report(today, path)
            self.assertEqual(day, friday)
            self.assertTrue(url.endswith("/202611/stq_20261113.pdf"))
            self.assertTrue(download.call_args_list[0].args[0].endswith("stq_20261116.pdf"))
            self.assertEqual(download.call_count, 2)
            self.assertEqual(path.read_bytes(), b"friday")

    def test_rejects_mismatched_report_without_replacing_output(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "latest.pdf"
            path.write_bytes(b"existing")
            with patch.object(daily, "download", return_value=b"wrong"), \
                 patch.object(daily, "trading_date", return_value=date(2026, 11, 13)):
                with self.assertRaisesRegex(ValueError, "report date does not match"):
                    daily.latest_report(date(2026, 11, 17), path)
            self.assertEqual(path.read_bytes(), b"existing")
            self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == "__main__":
    main()
