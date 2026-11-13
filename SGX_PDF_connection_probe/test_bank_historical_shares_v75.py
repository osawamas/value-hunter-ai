"""O39/U11 dated treasury shares: synthetic issuer PDF and negative cases."""
import tempfile, unittest
from pathlib import Path
import fitz
from bank_historical_shares_v75 import CONFIG,parse_pdf,run


def pdf(symbol,wrong_count=False,wrong_date=False,subsidiary=False,duplicate=False):
    spec=CONFIG[symbol]
    doc=fitz.open()
    for _ in range(spec["page"]):
        doc.new_page(width=1150,height=830)
    doc[0].insert_text((20,20),"OCBC Annual Report 2025" if symbol=="O39" else "UOB Annual Report 2025")
    page=doc[spec["page"]-1]
    if symbol=="O39":
        lines=[
            "Shareholding Statistics",
            "As at "+("25 February 2025" if wrong_date else "25 February 2026"),
            "Number of issued shares (including treasury shares): "+f"{spec['gross']+(1 if wrong_count else 0):,}",
            "Number of treasury shares held: 10,523,722",
            "Number of subsidiary holdings held: "+("1" if subsidiary else "Nil"),
        ]
    else:
        lines=[
            "Statistics of Shareholdings",
            "as at "+("23 February 2025" if wrong_date else "23 February 2026"),
            "Distribution of Shareholdings",
            "Total",
            "67,735",
            "100.00",
            f"{spec['net']+(1 if wrong_count else 0):,}",
            "100.00",
            "Treasury shares, subsidiary holdings and public float",
            "As at 23 February 2026, the Company had 15,243,008 treasury shares",
            "and no subsidiary holdings.",
        ]
    if duplicate:
        lines.append(lines[2] if symbol=="O39" else f"Total 67,735 100.00 {spec['net']:,} 100.00")
    for i,line in enumerate(lines):
        page.insert_text((20,32+45*i),line,fontsize=11)
    raw=doc.tobytes();doc.close()
    return raw

class HistoricalShareTests(unittest.TestCase):
    def test_both_issuers_net_treasury(self):
        for symbol in ("O39","U11"):
            snapshot=parse_pdf(symbol,pdf(symbol))
            self.assertEqual(snapshot["gross_issued_shares"]-snapshot["treasury_shares"],
                             snapshot["issued_excluding_treasury"])
            self.assertEqual(snapshot["as_of_date"],CONFIG[symbol]["date"])
            self.assertFalse(snapshot["market_cap_or_ranking_eligible"])
    def test_wrong_count_rejected(self):
        for symbol in ("O39","U11"):
            with self.assertRaises(ValueError):
                parse_pdf(symbol,pdf(symbol,wrong_count=True))
    def test_wrong_date_rejected(self):
        for symbol in ("O39","U11"):
            with self.assertRaises(ValueError):parse_pdf(symbol,pdf(symbol,wrong_date=True))
    def test_subsidiary_holdings_fail_closed(self):
        with self.assertRaises(ValueError):parse_pdf("O39",pdf("O39",subsidiary=True))
    def test_invalid_source_never_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            r=run("U11",Path(d)/"out.json",raw=b"<html>blocked")
            self.assertEqual(r["status"],"NOT_VERIFIED")
            self.assertIsNone(r["record"])
    def test_duplicate_issuer_gross_rejected(self):
        with self.assertRaises(ValueError):
            parse_pdf("O39",pdf("O39",duplicate=True))

if __name__=="__main__":unittest.main()
