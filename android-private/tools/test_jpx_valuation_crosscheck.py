from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock, patch

from jpx_hachiquant_coverage import verified_valuation_rows


class ValuationCrosscheckTest(TestCase):
    def test_originals_are_checked_even_when_rights_are_unverified(self):
        day = date(2026, 11, 26)
        row = {"currency": "JPY", "span": "FY", "source_doc_id": "S100AB12",
               "period_end": "2026-03-31", "latest_filing_date": "2026-06-24",
               "metrics": {"eps": Decimal("10"), "bvps": Decimal("500")}}
        original = Mock()
        original.check.return_value = dict(
            filing_metadata_match=True, full_year_verified=True, per_share_facts_match=True,
            original_period_end_share_count_present=True)
        with patch("jpx_hachiquant_coverage.share_basis_status", return_value="hold_rights_report_gap"):
            verified, counts = verified_valuation_rows(
                day, {"1301": "prime"}, {"1301": row}, (set(), {}), {}, original, 40)
        self.assertEqual(verified, {})
        self.assertEqual(counts["original_rows_verified"], 1)
        self.assertEqual(counts["share_basis_unverified"], 1)

    def test_rotates_through_submission_date_batches(self):
        day = date(2026, 11, 26)
        rows = {
            code: {"currency": "JPY", "span": "FY", "source_doc_id": "S100AB12",
                   "period_end": "2026-03-31", "latest_filing_date": filed,
                   "metrics": {"eps": Decimal("10"), "bvps": Decimal("500")}}
            for code, filed in (("1301", "2026-06-24"), ("1302", "2026-07-20"), ("1303", "2026-06-24"))
        }
        original = Mock()
        original.check.return_value = dict(
            filing_metadata_match=True, full_year_verified=True, per_share_facts_match=True,
            original_period_end_share_count_present=True)
        with patch("jpx_hachiquant_coverage.share_basis_status",
                   return_value="no_share_change_in_supplied_reports"):
            verified, counts = verified_valuation_rows(
                day, dict.fromkeys(rows), rows, (set(), {}), {}, original, 2, batch=1)
        self.assertEqual(set(verified), {"1302"})
        self.assertEqual(counts["batch_offset"], 2)
        original.check.assert_called_once()
