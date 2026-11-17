import unittest

from sgx_property_coverage import parse_counter_codes


def page(codes):
    header = (
        "Key Statistics for S-REITs & Property Trusts\n"
        "Name     Stock code     Property Sub Segment"
    )
    rows = [f"ISSUER {index}^#      {code}      Retail" for index, code in enumerate(codes)]
    return "\n".join([header, *rows, "Source: SGX, data as of 30 September 2026"])


class PropertyCoverageTests(unittest.TestCase):
    def test_reads_exact_codes_and_rejects_duplicate_or_incomplete_report(self):
        first = page([f"A{index:02}" for index in range(17)])
        second = page([f"B{index:02}" for index in range(22)])
        result = parse_counter_codes(first + "\f" + second)
        self.assertEqual(len(result), 39)
        self.assertEqual(result["B21"], "ISSUER 21")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_counter_codes(first + "\f" + second.replace("B21", "A00"))
        with self.assertRaisesRegex(ValueError, "39"):
            parse_counter_codes(first + "\f" + second.replace("B21", ""))
