"""Offline tests for checksum-verified private JP financial PDF acquisition."""
import hashlib
import io
import json
from unittest.mock import patch
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from jpx_financial_source_fetch import fetch, validate, main


class FakeResponse(io.BytesIO):
    headers = {}


class FakeOpener:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        return FakeResponse(self.data)


class SourceFetchTest(unittest.TestCase):
    def setUp(self):
        self.data = b"%PDF-1.4\nprivate test original\n%%EOF\n"
        self.record = {
            "code": "1234",
            "url": "https://issuer.example/annual.pdf",
            "sha256": hashlib.sha256(self.data).hexdigest(),
        }

    def test_download_then_cached_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = FakeOpener(self.data)
            self.assertEqual(fetch(self.record, Path(directory), {"issuer.example"}, opener), "downloaded")
            self.assertEqual(fetch(self.record, Path(directory), {"issuer.example"}, opener), "cached")
            self.assertEqual(opener.calls, 1)

    def test_reject_unapproved_host(self):
        with self.assertRaises(ValueError):
            validate(self.record, {"another.example"})

    def test_reject_wrong_digest_without_storing(self):
        with tempfile.TemporaryDirectory() as directory:
            record = dict(self.record, sha256="0" * 64)
            with self.assertRaises(ValueError):
                fetch(record, Path(directory), {"issuer.example"}, FakeOpener(self.data))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_private_audit_report_records_cache_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fetch(self.record, root / 'pdf', {'issuer.example'}, FakeOpener(self.data))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([self.record, {'code': 'bad'}]), encoding='utf-8')
            report = root / 'audit.json'
            with patch('sys.argv', ['fetch', str(manifest), str(root / 'pdf'),
                                    '--allowed-host', 'issuer.example', '--report', str(report)]):
                with self.assertRaises(SystemExit) as result:
                    main()
            self.assertEqual(result.exception.code, 1)
            audit = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(audit['summary']['cached'], 1)
            self.assertEqual(audit['summary']['failed'], 1)
            self.assertEqual([r['status'] for r in audit['sources']], ['cached', 'failed'])
            self.assertEqual(audit['summary']['financial_records_verified'], 0)

    def test_reject_non_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b"not a pdf"
            record = dict(self.record, sha256=hashlib.sha256(data).hexdigest())
            with self.assertRaises(ValueError):
                fetch(record, Path(directory), {"issuer.example"}, FakeOpener(data))


if __name__ == "__main__":
    unittest.main()
