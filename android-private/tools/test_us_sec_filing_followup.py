from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from us_sec_filing_followup import check

CUTOFF = date(2026, 11, 16)


def index(path, received, rows):
    header = ("Description: Master Index of EDGAR Dissemination Feed\n"
              f"Last Data Received: {received}\n\n"
              "CIK|Company Name|Form Type|Date Filed|Filename\n---\n")
    path.write_text(header + "\n".join(rows) + "\n")
    return path


def filing(cik, form, day, number):
    return f"{cik}|Issuer|{form}|{day}|edgar/data/{cik}/{cik:010d}-26-{number:06d}.txt"


class FollowupTest(unittest.TestCase):
    def test_excludes_source_filing_and_flags_later_relevant_form(self):
        with TemporaryDirectory() as directory:
            path = index(Path(directory) / "q4.idx", "November 16, 2026", [
                filing(1, "10-Q", "2026-10-31", 1), filing(1, "424B5", "2026-11-01", 2),
                filing(2, "10-Q", "2026-10-29", 1), filing(2, "4", "2026-11-16", 2),
                filing(4, "8-K", "2026-11-16", 3),
            ])
            result = check(
                {(2026, 4): path}, CUTOFF,
                {1: date(2026, 10, 25), 2: date(2026, 10, 25), 3: date(2026, 9, 30), 4: CUTOFF},
                {cik: f"{cik:010d}-26-000001".encode() for cik in (1, 2, 3, 4)},
                {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4},
                {"Nasdaq": {"ONE": 1, "TWO": 2}},
            )
        self.assertEqual(2, result["filing_needs_review"])
        self.assertEqual(1, result["with_registration_or_prospectus"])
        self.assertEqual(1, result["no_selected_form_detected"])
        self.assertEqual(1, result["index_interval_incomplete"])
        self.assertEqual(1, result["by_market_or_index"]["Nasdaq"]["filing_needs_review"])

    def test_rejects_truncated_index_and_wrong_quarter(self):
        with TemporaryDirectory() as directory:
            path = index(Path(directory) / "q4.idx", "November 16, 2026", [
                filing(1, "8-K", "2026-11-13", 1),
            ])
            for expected in ((2026, 4), (2026, 3)):
                with self.subTest(expected=expected), self.assertRaises(ValueError):
                    check({expected: path}, CUTOFF, {}, {}, {}, {})

    def test_combines_adjacent_quarters_before_reporting_no_selected_forms(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                (2026, 3): index(root / "q3.idx", "September 30, 2026", [filing(1, "4", "2026-09-30", 1)]),
                (2026, 4): index(root / "q4.idx", "November 16, 2026", [filing(1, "8-K/A", "2026-11-16", 2)]),
            }
            result = check(paths, CUTOFF, {1: date(2026, 9, 29)}, {1: b"0000000001-26-000002"}, {"ONE": 1}, {})
        self.assertEqual(0, result["index_interval_incomplete"])
        self.assertEqual(1, result["no_selected_form_detected"])


if __name__ == "__main__":
    unittest.main()
