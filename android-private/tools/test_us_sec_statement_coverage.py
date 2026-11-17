from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from us_sec_statement_coverage import measure

CUTOFF = date(2026, 11, 16)
PERIOD = "20260930"


def submission(accession, cik, filed="20261112", form="10-Q", period=PERIOD):
    return (accession, str(cik), form, period, filed)


def fact(accession, tag, value, quarters, period=PERIOD, segment="", unit="USD"):
    return (accession, tag, "us-gaap/2026", period, quarters, unit, segment, "", value, "")


def pair(accession, period=PERIOD, quarters="1"):
    return [fact(accession, "StockholdersEquity", "100", "0", period),
            fact(accession, "NetIncomeLoss", "20", quarters, period)]


def archive(path, submissions, facts):
    with ZipFile(path, "w") as output:
        output.writestr("sub.txt", "adsh\tcik\tform\tperiod\tfiled\n"
                        + "\n".join("\t".join(row) for row in submissions) + "\n")
        output.writestr("num.txt", "adsh\ttag\tversion\tddate\tqtrs\tuom\tsegments\tcoreg\tvalue\tfootnote\n"
                        + "\n".join("\t".join(row) for row in facts) + "\n")
    return path


class StatementCoverageTest(unittest.TestCase):
    def test_rejects_same_day_later_and_amended_filings(self):
        with TemporaryDirectory() as directory:
            source = archive(Path(directory) / "facts.zip", [
                submission("okay", 1), submission("same", 2, "20261116"),
                submission("later", 3, "20261117"), submission("amended", 4, form="10-Q/A"),
            ], pair("okay") + pair("same") + pair("later") + pair("amended"))
            counts = measure([source], CUTOFF, {"ONE.A": 1, "ONE.B": 1, "SAME": 2, "LATER": 3, "AM": 4})
        self.assertEqual(2, counts["securities_with_original_10k_or_10q"])
        self.assertEqual(2, counts["securities_with_equity_and_period_profit"])
        self.assertEqual(1, counts["unique_issuers_with_equity_and_period_profit"])

    def test_rejects_conflicts_and_uses_latest_filing_across_archives(self):
        with TemporaryDirectory() as directory:
            earlier_period = "20260630"
            early = archive(Path(directory) / "early.zip", [
                submission("early", 1, filed="20260820", period=earlier_period),
                submission("only-early", 2, filed="20260820", period=earlier_period),
            ], pair("early", earlier_period) + pair("only-early", earlier_period))
            newest = archive(Path(directory) / "newest.zip", [
                submission("conflict", 1), submission("annual", 3, form="10-K"),
                submission("missing", 4),
            ], pair("conflict") + [fact("conflict", "NetIncomeLoss", "21", "1")]
                + pair("annual", quarters="4")
                + [fact("missing", "StockholdersEquity", "999", "0", segment="subsidiary"),
                   fact("missing", "StockholdersEquity", "333", "0", unit="EUR"),
                   fact("missing", "NetIncomeLoss", "30", "1")])
            counts = measure([newest, early], CUTOFF, {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4})
        self.assertEqual(4, counts["securities_with_original_10k_or_10q"])
        self.assertEqual(2, counts["securities_with_equity_and_period_profit"])

    def test_refuses_zip_without_required_tables(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.zip"
            with ZipFile(path, "w") as output:
                output.writestr("unexpected.txt", "bad")
            with self.assertRaises(KeyError):
                measure([path], CUTOFF, {"ONE": 1})


if __name__ == "__main__":
    unittest.main()
