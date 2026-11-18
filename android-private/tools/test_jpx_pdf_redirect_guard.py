"""Regression test: a custom HTTP opener must not bypass manifest URL pinning."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("jpx_financial_source_fetch.py")
spec = importlib.util.spec_from_file_location("jpx_financial_source_fetch", MODULE)
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class RedirectResponse:
    headers = {}
    def __init__(self, url):
        self.url = url
    def geturl(self):
        return self.url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        raise AssertionError("redirected response must never be read")


class RedirectOpener:
    def open(self, request, timeout):
        return RedirectResponse("https://other.example/changed.pdf")


class RedirectGuardTest(unittest.TestCase):
    def test_custom_opener_redirect_is_rejected_before_read(self):
        entry = {"code": "1234", "url": "https://issuer.example/report.pdf",
                 "sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Redirected original"):
                fetcher.fetch(entry, Path(directory), {"issuer.example"}, RedirectOpener())
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
