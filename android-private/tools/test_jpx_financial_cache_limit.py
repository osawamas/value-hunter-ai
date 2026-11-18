"""Regression: cached issuer originals must obey the download size limit."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from jpx_financial_source_fetch import fetch


class CacheLimitTest(unittest.TestCase):
    def test_oversized_cache_rejected_without_reading_content(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            data = b"%PDF-1.4\n"
            digest = hashlib.sha256(data).hexdigest()
            entry = {"code": "1234", "url": "https://issuer.example/report.pdf",
                     "sha256": digest}
            target = directory / ("1234-" + digest[:16] + ".pdf")
            target.write_bytes(data)
            with patch("jpx_financial_source_fetch.MAX_BYTES", len(data) - 1):
                with self.assertRaisesRegex(ValueError, "size limit"):
                    fetch(entry, directory, {"issuer.example"})

    def test_valid_cache_reused(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            data = b"%PDF-1.4\nvalid"
            digest = hashlib.sha256(data).hexdigest()
            entry = {"code": "1234", "url": "https://issuer.example/report.pdf",
                     "sha256": digest}
            (directory / ("1234-" + digest[:16] + ".pdf")).write_bytes(data)
            self.assertEqual(fetch(entry, directory, {"issuer.example"}), "cached")


if __name__ == "__main__":
    unittest.main()
