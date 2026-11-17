from datetime import date
import unittest

from us_sec_original_cover import instance_path, original_share_count, resolve_tickers

FILED = date(2026, 11, 3)
ACCESSION = "0000320193-26-000026"
FOLDER = "/Archives/edgar/data/320193/000032019326000026/"


def instance(decimals="0", segment="", count="123000", day="2026-10-23"):
    return f"""<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2026">
      <context id="cover"><entity>
        <identifier scheme="http://www.sec.gov/CIK">0000320193</identifier>{segment}
      </entity><period><instant>{day}</instant></period></context>
      <unit id="s"><measure>shares</measure></unit>
      <dei:EntityCommonStockSharesOutstanding contextRef="cover" unitRef="s" decimals="{decimals}">{count}</dei:EntityCommonStockSharesOutstanding>
    </xbrl>""".encode()


class OriginalCoverTest(unittest.TestCase):
    def test_reads_exact_and_rounded_disclosures_separately(self):
        self.assertEqual((date(2026, 10, 23), 123000, 0), original_share_count(instance(), 320193, FILED))
        self.assertEqual((date(2026, 10, 23), 123000, -3),
                         original_share_count(instance(decimals="-3"), 320193, FILED))

    def test_rejects_other_issuer_later_shares_and_dimensions(self):
        for xml, cik in ((instance(), 42), (instance(day="2026-11-04"), 320193),
                         (instance(segment="<segment/>"), 320193)):
            with self.subTest(cik=cik, xml=xml), self.assertRaises(ValueError):
                original_share_count(xml, cik, FILED)

    def test_filing_links_must_be_same_accession_and_unique(self):
        valid = FOLDER + "aapl-20260926_htm.xml"
        related = valid.replace("/320193/", "/42/")
        foreign = valid.replace("000032019326000026", "000032019326000025")
        self.assertEqual(related, instance_path(f'<a href="{related}">'.encode(), ACCESSION))
        for html in (f'<a href="{foreign}">', f'<a href="{valid}"><a href="{related}">', f'<a href="//bad{valid}">'):
            with self.subTest(html=html), self.assertRaises(ValueError):
                instance_path(html.encode(), ACCESSION)

    def test_unconfirmed_share_class_or_exchange_held(self):
        directory = {"A": {(1, "NYSE")}, "A.D": {(1, "NYSE")}, "B": {(2, "Nasdaq")},
                     "B.B": {(2, "Nasdaq")}, "C": {(3, "NYSE")}}
        listings = {"A": ("NYSE", "common_or_ordinary_label"), "A.D": ("NYSE", "other_security"),
                    "B": ("Nasdaq", "common_or_ordinary_label"), "C": ("Nasdaq", "common_or_ordinary_label")}
        selected, held = resolve_tickers(["A", "B", "C"], directory, listings)
        self.assertEqual({"A": 1}, selected)
        self.assertEqual({"B", "C"}, held.keys())


if __name__ == "__main__":
    unittest.main()
