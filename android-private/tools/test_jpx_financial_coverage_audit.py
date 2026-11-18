"""Regression tests for JPX source-versus-issuer coverage counts."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jpx_financial_source_fetch as module


class CoverageAuditTests(unittest.TestCase):
    def test_duplicate_and_mixed_source_records_are_not_double_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            report = root / "report.json"
            records = [
                {"code": "1234", "url": "https://issuer.example/a.pdf", "sha256": "a" * 64},
                {"code": "1234", "url": "https://issuer.example/b.pdf", "sha256": "b" * 64},
                {"code": "5678", "url": "https://issuer.example/c.pdf", "sha256": "c" * 64},
            ]
            manifest.write_text(json.dumps(records), encoding="utf-8")
            def fake_fetch(entry, destination, hosts):
                if entry["sha256"].startswith("b"):
                    raise ValueError("source unavailable")
                return "downloaded"
            argv = ["fetch", str(manifest), str(root / "pdf"), "--allowed-host",
                    "issuer.example", "--report", str(report)]
            with patch.object(sys, "argv", argv), patch.object(module, "fetch", side_effect=fake_fetch):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exit_result:
                        module.main()
            self.assertEqual(exit_result.exception.code, 1)
            summary = json.loads(report.read_text(encoding="utf-8"))["summary"]
            self.assertEqual(summary["source_records"], 3)
            self.assertEqual(summary["downloaded"], 2)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["distinct_codes"], 2)
            self.assertEqual(summary["codes_with_source"], 2)
            self.assertEqual(summary["codes_with_failed_source"], 1)
            self.assertEqual(summary["codes_with_mixed_source_results"], 1)
            self.assertEqual(summary["financial_records_verified"], 0)


if __name__ == "__main__":
    unittest.main()
