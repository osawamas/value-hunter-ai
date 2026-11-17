from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from us_sec_statement_coverage import Filing, INCOME, fact_key, measure, trailing_profit

CUTOFF = date(2026, 11, 16)
PERIOD = "20260930"


def submission(accession, cik, filed="20261112", form="10-Q", period=PERIOD, year="2026", focus=None):
    return (accession, str(cik), form, period, filed, year, focus or ("FY" if form == "10-K" else "Q3"))


def fact(accession, tag, value, quarters, period=PERIOD, segment="", unit="USD"):
    return (accession, tag, "us-gaap/2026", period, quarters, unit, segment, "", value, "")


def pair(accession, period=PERIOD, quarters="1"):
    return [fact(accession, "StockholdersEquity", "100", "0", period),
            fact(accession, "NetIncomeLoss", "20", quarters, period)]


def archive(path, submissions, facts):
    with ZipFile(path, "w") as output:
        output.writestr("sub.txt", "adsh\tcik\tform\tperiod\tfiled\tfy\tfp\n"
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
            counts = measure([source], CUTOFF, {"ONE.A": 1, "ONE.B": 1, "SAME": 2, "LATER": 3, "AM": 4},
                             {"Nasdaq": {"ONE.A": 1}, "NYSE": {"SAME": 2}}, {1: date(2026, 10, 23)})
        self.assertEqual(2, counts["securities_with_original_10k_or_10q"])
        self.assertEqual(2, counts["securities_with_equity_and_period_profit"])
        self.assertEqual(1, counts["unique_issuers_with_equity_and_period_profit"])
        groups = counts["by_market_or_index"]
        self.assertEqual(1, groups["Nasdaq"]["securities_with_equity_and_period_profit"])
        self.assertEqual(0, groups["NYSE"]["unique_issuers_with_equity_and_period_profit"])

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
            counts = measure([newest, early], CUTOFF, {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4},
                             share_dates={1: date(2026, 10, 23), 3: date(2026, 10, 25)})
        self.assertEqual(4, counts["securities_with_original_10k_or_10q"])
        self.assertEqual(2, counts["securities_with_equity_and_period_profit"])
        self.assertEqual(1, counts["with_equity_trailing_profit_and_dated_cover_shares"])

    def test_trailing_income_uses_matching_fiscal_windows_and_no_conflicting_amounts(self):
        with TemporaryDirectory() as directory:
            annuals = []
            quarterlies = []
            for cik in range(1, 5):
                annual = f"annual-{cik}"
                annual_period = "20251130" if cik == 3 else "20251231"
                filed = "20261116" if cik == 4 else "20260220"
                annuals.append(submission(annual, cik, filed, "10-K", annual_period, "2025"))
                quarterlies.append(submission(f"latest-{cik}", cik, "20260813", period="20260630", focus="Q2"))
            annual_facts = [fact(f"annual-{cik}", "NetIncomeLoss", "100", "4",
                                 "20251130" if cik == 3 else "20251231") for cik in range(1, 5)]
            quarterly_facts = []
            for cik in range(1, 5):
                accession = f"latest-{cik}"
                quarterly_facts.extend(pair(accession, "20260630"))
                quarterly_facts.extend([
                    fact(accession, "NetIncomeLoss", "55", "2", "20260630"),
                    fact(accession, "NetIncomeLoss", "38", "2", "20250630"),
                ])
            quarterly_facts.append(fact("latest-2", "NetIncomeLoss", "39", "2", "20250630"))
            first = archive(Path(directory) / "early.zip", annuals, annual_facts)
            second = archive(Path(directory) / "late.zip", quarterlies, quarterly_facts)
            counts = measure([first, second], CUTOFF, {f"STOCK{cik}": cik for cik in range(1, 5)})
        self.assertEqual(4, counts["securities_with_equity_and_period_profit"])
        self.assertEqual(1, counts["securities_with_equity_and_trailing_profit"])

    def test_trailing_profit_is_annual_plus_same_length_ytd_change(self):
        annual = Filing(b"annual", b"10-K", date(2025, 12, 31), date(2026, 2, 20), 2025, b"FY")
        latest = Filing(b"latest", b"10-Q", date(2026, 6, 30), date(2026, 8, 13), 2026, b"Q2")
        facts = {
            fact_key(annual, INCOME, annual.period, 4): {Decimal("100")},
            fact_key(latest, INCOME, latest.period, 2): {Decimal("55")},
            fact_key(latest, INCOME, date(2025, 6, 30), 2): {Decimal("38")},
        }
        self.assertEqual(Decimal("117"), trailing_profit(latest, annual, facts))

    def test_refuses_zip_without_required_tables(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.zip"
            with ZipFile(path, "w") as output:
                output.writestr("unexpected.txt", "bad")
            with self.assertRaises(KeyError):
                measure([path], CUTOFF, {"ONE": 1})


if __name__ == "__main__":
    unittest.main()
