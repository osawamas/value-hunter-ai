import unittest

from sgx_sti_coverage import parse_sti_pdf_layout


def table():
    header = (
        "FTSE Russell Publications\nSTI     19 August 2026\n"
        "Indicative Index Weight Data as at Closing on 30 June 2026\n"
    )
    rows = ["Constituent".ljust(50) * 3, "Percent".ljust(50) * 3]
    for number in range(10):
        rows.append("".join(
            f"Issuer {column}-{number}     1.00     SINGAPORE".ljust(50)
            for column in range(3)
        ))
        if number == 0:
            rows.append("Trust")
    return header + "\n".join([*rows, "Source: FTSE Russell"])


class StiCoverageTests(unittest.TestCase):
    def test_reads_all_columns_and_preserves_wrapped_names(self):
        as_of, names = parse_sti_pdf_layout(table())
        self.assertEqual(as_of, "2026-06-30")
        self.assertEqual(len(names), 30)
        self.assertEqual(names[0], "Issuer 0-0 Trust")
        self.assertEqual(names[-1], "Issuer 2-9")

    def test_rejects_partial_or_duplicate_tables(self):
        with self.assertRaisesRegex(ValueError, "30 distinct"):
            parse_sti_pdf_layout(table().replace("Issuer 0-9", "Issuer 0-8"))
        with self.assertRaisesRegex(ValueError, "30 distinct"):
            parse_sti_pdf_layout(table().split("Issuer 0-9")[0])
