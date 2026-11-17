import unittest

from sgx_next50_coverage import compare_constituents, parse_constituents


class Next50CoverageTests(unittest.TestCase):
    def test_requires_two_complete_constituent_pages(self):
        def page(first):
            return (
                "SGX Monthly Market Statistics October 2026\n"
                "iEdge Singapore Next 50\nConstituent Name      Closing Price\n"
                + "\n".join(f"Issuer {number}       1.00" for number in range(first, first + 25))
            )
        self.assertEqual(len(parse_constituents(page(0) + "\f" + page(25))), 50)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_constituents(page(0) + "\f" + page(24))
        with self.assertRaisesRegex(ValueError, "both"):
            parse_constituents(page(0))

    def test_aliases_and_same_isin_counters_work_but_conflicts_are_reported(self):
        rows = {
            "AWX": {"symbol": "AWX", "isin": "A", "issuer": "AEM Holdings Ltd."},
            "XWA": {"symbol": "XWA", "isin": "A", "issuer": "AEM Holdings Ltd."},
            "NTDU": {"symbol": "NTDU", "isin": "B", "issuer": "NTT DC REIT USD"},
            "C01": {"symbol": "C01", "isin": "C", "issuer": "Other Ltd."},
            "C02": {"symbol": "C02", "isin": "D", "issuer": "Other Corporation"},
        }
        audit = compare_constituents(["AEM Holdings Ltd", "NTT DC REIT", "Other Ltd", "Missing"], rows)
        self.assertEqual(audit["matches"], {"AEM Holdings Ltd": ["AWX", "XWA"], "NTT DC REIT": ["NTDU"]})
        self.assertEqual(audit["ambiguous_names"], ["Other Ltd"])
        self.assertEqual(audit["missing_names"], ["Missing"])
