import io
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from decimal import Decimal
from zipfile import ZipFile

from jpx_edinet_crosscheck import BPS, EPS, SHARES, PER_SHARE_PAIRS, EdinetAudit, compare, download, facts_from_csv, metadata_matches


class CrossCheckTest(unittest.TestCase):
    def test_filing_identity_and_date(self):
        row = dict(docID="S100AB12", secCode="13010", periodEnd="2026-03-31",
                   submitDateTime="2026-06-24 10:12", docTypeCode="120",
                   withdrawalStatus="0", disclosureStatus="0", csvFlag="1")
        args = ("1301", "S100AB12", "2026-03-31", "2026-06-24")
        self.assertTrue(metadata_matches([row], *args))
        self.assertFalse(metadata_matches([row, row], *args))
        self.assertFalse(metadata_matches([dict(row, withdrawalStatus="1")], *args))
        self.assertFalse(metadata_matches([row], *args[:-1], "2026-06-25"))

    def test_download_does_not_expose_authenticated_url_on_error(self):
        key = "sample-key-that-must-not-appear"
        with patch("jpx_edinet_crosscheck.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "https://edinet.invalid/?Subscription-Key=" + key, 429, key, None, None)
            with self.assertRaises(HTTPError) as captured:
                download(".json", {"date": "2026-06-24", "type": 2}, key, 100)
        self.assertEqual(captured.exception.code, 429)
        self.assertNotIn(key, str(captured.exception))
        self.assertNotIn(key, captured.exception.url)

    def test_reuses_a_day_listing_and_propagates_document_throttling(self):
        listing = b'{"results":[]}'
        audit = EdinetAudit("test-key")
        with patch.object(audit, "request", return_value=listing) as request:
            for code in ("1301", "1302"):
                self.assertFalse(audit.check(
                    dict(code=code, annual_source_id="S100AB12", actual_filing_date="2026-06-24"),
                    {"period_end": "2026-03-31"})["filing_metadata_match"])
            self.assertEqual(request.call_count, 1)
        audit.days["2026-06-24"] = [dict(
            docID="S100AB12", secCode="13010", periodEnd="2026-03-31", periodStart="2025-04-01",
            submitDateTime="2026-06-24 10:12", docTypeCode="120", withdrawalStatus="0",
            disclosureStatus="0", csvFlag="1")]
        with patch.object(audit, "request", side_effect=HTTPError("https://edinet.invalid", 503, "", None, None)):
            with self.assertRaises(HTTPError):
                audit.check(dict(code="1301", annual_source_id="S100AB12", actual_filing_date="2026-06-24"),
                            {"period_end": "2026-03-31"})

    def test_later_filing_distinguishes_no_match_and_amendment_from_interim(self):
        audit = EdinetAudit("test-key")
        filed = "2026-11-06"
        args = ("1301", filed, "2026-03-31", Decimal("100"), Decimal("20000"))
        audit.days[filed] = []
        self.assertEqual(audit.review_newer(*args)["status"], "latest_no_edinet_filing_on_hint_date")
        row = dict(docID="S100AB12", secCode="13010", periodEnd="2026-09-30",
                   submitDateTime=filed + " 10:12", withdrawalStatus="0", disclosureStatus="0", csvFlag="1")
        audit.days[filed] = [dict(row, docTypeCode="160"), dict(row, docTypeCode="180")]
        facts = {(SHARES, "CurrentInterimInstant"): {Decimal("20000")},
                 (BPS, "CurrentInterimInstant"): {Decimal("110")}}
        with patch.object(audit, "request", return_value=b"csv"), patch(
                "jpx_edinet_crosscheck.facts_from_csv", return_value=facts):
            result = audit.review_newer(*args)
        self.assertEqual((result["status"], result["shares"], result["bps"]),
                         ("latest_interim_reviewed", "unchanged", "changed"))
        audit.days[filed] = [dict(row, docTypeCode="160", csvFlag="0", xbrlFlag="1")]
        denied = audit.review_newer(*args)
        self.assertEqual(denied["status"], "latest_interim_csv_not_offered")
        self.assertEqual((denied["doc_id"], denied["period_end"], denied["xbrl_flag"]),
                         ("S100AB12", "2026-09-30", "1"))
        audit.days[filed].append(dict(row, docTypeCode="170"))
        self.assertEqual(audit.review_newer(*args)["status"], "latest_annual_or_amendment_requires_review")

    def test_matches_standard_pairs_without_combining_accounting_standards(self):
        ifrs_eps, ifrs_bps = PER_SHARE_PAIRS[1]
        facts = {(ifrs_eps, "CurrentYearDuration"): {Decimal("10")},
                 (ifrs_bps, "CurrentYearInstant"): {Decimal("100")}}
        self.assertTrue(compare({"eps": 10, "bvps": 100}, facts)["per_share_facts_match"])
        facts[(BPS, "CurrentYearInstant")] = facts.pop((ifrs_bps, "CurrentYearInstant"))
        self.assertFalse(compare({"eps": 10, "bvps": 100}, facts)["per_share_facts_match"])

    def test_requires_same_scope_and_ignores_wrong_currency(self):
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            rows = ["要素ID\tコンテキストID\tユニットID\t値",
                    f"{EPS}\tCurrentYearDuration\tJPYPerShares\t-20.25",
                    f"{BPS}\tCurrentYearInstant\tJPYPerShares\t401.75",
                    f"{BPS}\tCurrentYearInstant\tUSDPerShares\t40",
                    f"{BPS}\tCurrentYearInstant_NonConsolidatedMember\tJPYPerShares\t410",
                    f"{SHARES}\tCurrentYearInstant_NonConsolidatedMember\tshares\t200000"]
            archive.writestr("XBRL_TO_CSV/jpcrp030000-asr-test.csv", "\n".join(rows).encode("utf-16"))
        facts = facts_from_csv(output.getvalue())
        self.assertEqual(compare(dict(eps=Decimal("-20.25"), bvps=Decimal("401.75")), facts),
                         dict(per_share_facts_match=True, original_period_end_share_count_present=True))
        self.assertFalse(compare(dict(eps=Decimal("-20.25"), bvps=410), facts)["per_share_facts_match"])


if __name__ == "__main__":
    unittest.main()
