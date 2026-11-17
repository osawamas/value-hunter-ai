"""Regression tests for JPX source provenance and conflicting daily editions."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
from datetime import date

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


if __name__ == "__main__":
    main()
