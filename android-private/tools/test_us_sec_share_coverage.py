from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from us_sec_share_coverage import NUM_HEADER, measure, share_date

CUTOFF = date(2026, 11, 16)


def row(accession, *, value="120", offset="8.0", precision="0", dimension="0x00000000",
        coreg="", tag="EntityCommonStockSharesOutstanding"):
    return (accession, tag, "dei/2026", "20261031", "0", "shares", dimension, "0", value,
            "", "0", "0" if dimension == "0x00000000" else "1", coreg, "0.0", offset, precision)


class ShareCoverageTest(unittest.TestCase):
    def test_recovers_dates_on_both_sides_of_month_end(self):
        self.assertEqual(date(2026, 10, 23), share_date(b"20261031", b"8.0"))
        self.assertEqual(date(2026, 10, 15), share_date(b"20260930", b"-15.0"))
        self.assertEqual(date(2026, 9, 30), share_date(b"20260930", b"0.0"))
        for bad in (b"-0.0645", b"19.0", b"NaN"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                share_date(b"20260930", bad)

    def test_keeps_unverified_share_counts_out_of_venue_totals(self):
        securities = {f"STOCK{i}": i for i in range(1, 8)}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "notes.zip"
            with ZipFile(path, "w") as archive:
                submissions = [
                    (f"a{i}", str(i), "10-Q", "20260930", "20261029" if i != 7 else "20261116", "2026", "Q3")
                    for i in range(1, 8)
                ]
                archive.writestr("sub.tsv", "adsh\tcik\tform\tperiod\tfiled\tfy\tfp\n"
                                 + "\n".join("\t".join(s) for s in submissions) + "\n")
                rows = [
                    row("a1"), row("a1", coreg="a subsidiary", dimension="0x11111111"),
                    row("a2", precision="-3"),
                    row("a3"), row("a3", value="121"),
                    row("a4"), row("a4", dimension="0x22222222"),
                    row("a5"), row("a6", tag="CommonStockSharesOutstanding"),
                    row("a7"),
                ]
                archive.writestr("num.tsv", b"\t".join(NUM_HEADER) + b"\n"
                                 + "\n".join("\t".join(fact) for fact in rows).encode() + b"\n")
            result, effective_dates = measure([path], CUTOFF, securities, {"NYSE": {"STOCK1": 1, "STOCK2": 2}}, {5})
        self.assertEqual({1: date(2026, 10, 23)}, effective_dates)
        self.assertEqual(1, result["with_dated_cover_share_count"])
        self.assertEqual(1, result["cover_date_within_30_days"])
        self.assertEqual(1, result["by_market_or_index"]["NYSE"]["with_dated_cover_share_count"])
        self.assertEqual({"class_detail_requires_review": 2, "date_precision_or_value_unconfirmed": 2,
                          "no_usable_cover_fact": 1, "no_eligible_filing": 1}, result["unconfirmed"])


if __name__ == "__main__":
    unittest.main()
