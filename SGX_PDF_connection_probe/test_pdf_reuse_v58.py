"""v58: two official S68 documents, four parsers, only two downloads.

The verified raw PDF is reused for follow-up parsers; it is never fetched
twice. A failed first-stage extraction must not create a reusable PDF copy.
No network request is made by these tests.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import s68_official_pdf_v44 as results
import s68_parent_equity_v54 as owner
import s68_shareholding_v46 as annual
import s68_annual_crosscheck_v50 as compare


class SourceReuseTests(unittest.TestCase):
    def test_results_pdf_one_fetch_two_extractors(self):
        raw = b"%PDF-synthetic-issuer-fy2026"
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cached = root / "verified_results.pdf"
            with patch.object(results, "download", side_effect=lambda: (calls.append(1), raw)[1]), \
                 patch.object(results, "parse_pdf", return_value={"ok": True}), \
                 patch.object(owner, "parse_pdf", return_value={"parent_equity": {"2026": 2362982}}), \
                 patch.object(owner, "download", side_effect=AssertionError("unexpected second download")):
                a = results.run(root / "financial.json", verified_pdf_copy=cached)
                b = owner.run(root / "owners.json", raw=cached.read_bytes())
            self.assertEqual(a["status"], "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED")
            self.assertEqual(b["status"], "AUDITED_ISSUER_GROUP_OWNER_COMPONENTS_RECONCILED")
            self.assertEqual(a["pdf_sha256"], b["pdf_sha256"])
            self.assertEqual(a["pdf_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(len(calls), 1)

    def test_annual_pdf_one_fetch_two_extractors(self):
        raw = b"%PDF-synthetic-issuer-annual-2026"
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cached = root / "verified_annual.pdf"
            with patch.object(annual, "fetch", side_effect=lambda: (calls.append(1), raw)[1]), \
                 patch.object(annual, "parse_pdf", return_value={"shares_outstanding": 1070843484}), \
                 patch.object(compare, "parse_pdf", return_value={
                     "revenue": [{"2026": 1559469, "2025": 1370625}],
                     "attributable_profit": [{"2026": 698411, "2025": 647983}]
                 }), \
                 patch.object(compare, "download", side_effect=AssertionError("unexpected second download")):
                a = annual.run(root / "shares.json", verified_pdf_copy=cached)
                b = compare.run(root / "crosscheck.json", raw=cached.read_bytes())
            self.assertEqual(a["status"], "OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED")
            self.assertEqual(b["status"], "SECOND_ISSUER_ANNUAL_REPORT_MATCHED")
            self.assertEqual(a["pdf_sha256"], b["pdf_sha256"])
            self.assertEqual(len(calls), 1)

    def test_bad_results_never_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cached = root / "verified_results.pdf"
            with patch.object(results, "parse_pdf", side_effect=ValueError("unverified")):
                rec = results.run(root / "financial.json", raw=b"%PDF-invalid", verified_pdf_copy=cached)
            self.assertEqual(rec["status"], "NOT_VERIFIED")
            self.assertFalse(cached.exists())

    def test_bad_annual_never_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cached = root / "verified_annual.pdf"
            with patch.object(annual, "parse_pdf", side_effect=ValueError("unverified")):
                rec = annual.run(root / "shares.json", raw=b"%PDF-invalid", verified_pdf_copy=cached)
            self.assertEqual(rec["status"], "NOT_VERIFIED")
            self.assertFalse(cached.exists())


if __name__ == "__main__":
    unittest.main()
