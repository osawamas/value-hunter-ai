"""Regression tests for JPX source provenance and conflicting daily editions."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
from datetime import date

from urllib.error import HTTPError

import jpx_android_rights_refresh as refresh
import jpx_daily_sources as daily
import jpx_rights_sources as sources


class SourceProvenanceTests(TestCase):
    def test_rapid_exclusions_require_both_dated_editions(self):
        with TemporaryDirectory() as temp, patch.object(sources, "page_links", return_value=[]), \
             patch.object(sources, "daily_sources", return_value=({"2026-11-18": {}}, {}, {})):
            with self.assertRaisesRegex(ValueError, "Both official JPX rights editions"):
                sources.verified_rapid_exclusions(date(2026, 11, 18), date(2026, 11, 19), Path(temp))

    def test_current_and_archived_monthly_links_stay_on_the_official_origin(self):
        index = """
        <option value="/markets/statistics-equities/monthly/index.html">2026年</option>
        <option value="/markets/statistics-equities/monthly/00-archives-01.html">2025年</option>
        <a href="today/17_kenri2609.pdf">Current</a>
        <a href="https://example.com/17_kenri2609.pdf">Untrusted</a>
        """.encode("utf-8")
        archive = b'<a href="/markets/statistics-equities/monthly/older/17_kenri2509.pdf">Archive</a>'
        with patch.object(sources, "download", side_effect=[index, archive]) as download:
            links = sources.monthly_archive_links({2025, 2026})
        self.assertEqual(links, {
            date(2025, 9, 1): "https://www.jpx.co.jp/markets/statistics-equities/monthly/older/17_kenri2509.pdf",
            date(2026, 9, 1): "https://www.jpx.co.jp/markets/statistics-equities/monthly/today/17_kenri2609.pdf",
        })
        self.assertEqual(download.call_count, 2)

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


class AndroidRightsRefreshTests(TestCase):
    first = date(2026, 3, 1)
    last = date(2026, 11, 1)
    month = "https://www.jpx.co.jp/month.pdf"
    old_notice = {"code": "6861", "exDay": "2026-11-19",
                  "source": "https://www.jpx.co.jp/20261111.xls"}
    existing = {"coveredCodes": ["6861"], "monthlySources": {"2026-09": month, "2026-10": month},
                "notices": [old_notice]}

    def test_dry_run_and_update_preserve_rolled_off_notices_but_reaudit_months(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "rights.json"
            old = json.dumps(self.existing)
            path.write_text(old, encoding="utf-8")
            fresh = {"coveredCodes": ["6861", "9432"], "monthlySources": {"2026-09": self.month},
                     "notices": []}
            with patch.object(refresh, "page_links", return_value=[]), \
                 patch.object(refresh, "daily_sources", return_value=(
                     {"2026-11-17": {}}, {}, {"event_keys_with_conflicting_ex_dates": 0})), \
                 patch.object(refresh, "monthly_sources", return_value=(
                     {"2026-09": 0}, {}, {"2026-10": {}}, ["2026-11"])), \
                 patch.object(refresh, "snapshot", return_value=fresh) as snapshot:
                result = refresh.refresh(path, self.first, self.last, dry_run=True, include_codes=["9432"])
                self.assertTrue(result["changed"])
                self.assertEqual(result["rejectedMonths"], ["2026-10"])
                self.assertEqual(path.read_text(encoding="utf-8"), old)
                refresh.refresh(path, self.first, self.last, include_codes=["9432"])
                self.assertEqual(snapshot.call_args.args[2], {"6861", "9432"})
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(updated["coveredCodes"], ["6861", "9432"])
            self.assertEqual(updated["monthlySources"], {"2026-09": self.month})
            self.assertEqual(updated["notices"], [self.old_notice])

    def test_failure_does_not_replace_original_snapshot(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "rights.json"
            old = json.dumps(self.existing)
            path.write_text(old, encoding="utf-8")
            with patch.object(refresh, "page_links", return_value=[]), \
                 patch.object(refresh, "daily_sources", side_effect=ValueError("Conflicting editions")):
                with self.assertRaisesRegex(ValueError, "Conflicting editions"):
                    refresh.refresh(path, self.first, self.last)
            self.assertEqual(path.read_text(encoding="utf-8"), old)


if __name__ == "__main__":
    main()
