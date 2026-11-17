import unittest

from sgx_public_directory import exclude_replaced_codes, parse_directory, supplement_directory, valid_isin

HTML = """
<p>record as of 2026-11-13</p>
<table>
<tr><th>exchange</th><th>code</th><th>listed companies with a page</th></tr>
<tr><td>Mainboard</td><td>SGX</td><td>1</td></tr>
<tr><td>Catalist</td><td>SGX-CATALIST</td><td>2</td></tr>
</table>
<table>
<tr><th>issuer</th><th>exchange</th><th>ticker</th><th>ISIN</th></tr>
<tr><td><a>Singapore Exchange Ltd.</a></td><td>SGX</td><td>S68</td><td>SG1J26887955</td></tr>
<tr><td>Astaka Holdings</td><td>SGX-CATALIST</td><td>42S</td><td>SG1CB5000005</td></tr>
<tr><td>Astaka Holdings</td><td>SGX-CATALIST</td><td>9SY</td><td>SGXE75609730</td></tr>
</table>
"""


class PublicDirectoryTests(unittest.TestCase):
    def test_keeps_distinct_codes_and_reads_both_boards(self):
        as_of, records, counts = parse_directory(HTML)
        self.assertEqual(as_of, "2026-11-13")
        self.assertEqual(counts, {"Mainboard": 1, "Catalist": 2})
        self.assertEqual(set(records), {"S68", "42S", "9SY"})

    def test_rejects_partial_html_and_mismatched_board_totals(self):
        for broken in (HTML.rsplit("</table>", 1)[0], HTML.replace("<td>2</td>", "<td>3</td>")):
            with self.assertRaises(ValueError):
                parse_directory(broken)

    def test_rejects_bad_isin_and_duplicate_code(self):
        self.assertTrue(valid_isin("SG1J26887955"))
        self.assertFalse(valid_isin("SG1J26887956"))
        for broken in (HTML.replace("87955", "87956"), HTML.replace("9SY", "42S")):
            with self.assertRaises(ValueError):
                parse_directory(broken)

    def test_applies_confirmed_replacement_only_to_exact_old_identity(self):
        as_of, records, _ = parse_directory(HTML)
        filtered, exclusions = exclude_replaced_codes(records, as_of)
        self.assertEqual(set(filtered), {"S68", "9SY"})
        self.assertEqual(exclusions[0]["old_symbol"], "42S")
        self.assertTrue(exclusions[0]["replacement_present"])
        self.assertFalse(exclude_replaced_codes(records, "2026-09-16")[1])
        self.assertFalse(exclude_replaced_codes({"42S": {"isin": "other"}}, as_of)[1])

    def test_keeps_two_currency_counters_with_the_same_isin(self):
        row = {
            "symbol": "AWX", "isin": "SG1BA1000003", "issuer": "AEM", "board": "Mainboard",
            "source_url": "https://links.sgx.com/example", "evidence_date": "2021-12-30",
            "security_type": "ordinary_share",
        }
        directory = {"XWA": {**row, "symbol": "XWA"}}
        merged, audit = supplement_directory(directory, [row])
        self.assertEqual(set(merged), {"AWX", "XWA"})
        self.assertEqual(audit["directory_missing_count"], 1)
        self.assertEqual(audit["unresolved_count"], 0)

    def test_never_overwrites_a_conflicting_code(self):
        row = {
            "symbol": "S68", "isin": "SG1J26887955", "issuer": "Singapore Exchange",
            "board": "Mainboard", "source_url": "https://links.sgx.com/example",
            "evidence_date": "2026-11-01", "security_type": "ordinary_share",
        }
        directory = {"S68": {**row, "isin": "SG1BA1000003"}}
        merged, audit = supplement_directory(directory, [row])
        self.assertEqual(merged, directory)
        self.assertEqual(audit["conflicting_codes"], ["S68"])
        self.assertEqual(audit["unresolved_count"], 1)
        with self.assertRaisesRegex(ValueError, "invalid SGX listing"):
            supplement_directory({}, [row, row])


if __name__ == "__main__":
    unittest.main()
