import io
import unittest
from decimal import Decimal
from zipfile import ZipFile

from jpx_edinet_crosscheck import BPS, EPS, SHARES, compare, facts_from_csv, metadata_matches


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

    def test_requires_same_scope_and_ignores_wrong_currency(self):
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            rows = ["要素ID\tコンテキストID\tユニットID\t値",
                    f"{EPS}\tCurrentYearDuration\tJPYPerShares\t-20.25",
                    f"{BPS}\tCurrentYearInstant\tJPYPerShares\t401.75",
                    f"{BPS}\tCurrentYearInstant\tUSDPerShares\t40",
                    f"{BPS}\tCurrentYearInstant_NonConsolidatedMember\tJPYPerShares\t410",
                    f"{SHARES}\tCurrentYearInstant_NonConsolidatedMember\tShares\t200000"]
            archive.writestr("XBRL_TO_CSV/jpcrp030000-asr-test.csv", "\n".join(rows).encode("utf-16"))
        facts = facts_from_csv(output.getvalue())
        self.assertEqual(compare(dict(eps=Decimal("-20.25"), bvps=Decimal("401.75")), facts),
                         dict(per_share_facts_match=True, original_period_end_share_count_present=True))
        self.assertFalse(compare(dict(eps=Decimal("-20.25"), bvps=410), facts)["per_share_facts_match"])


if __name__ == "__main__":
    unittest.main()
