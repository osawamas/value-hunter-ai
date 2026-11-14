"""v108: both bank identifiers tied to single official dated announcements only."""
import unittest
from sgx_bank_isin_v108 import SOURCES, parse

def fixture(symbol):
    c=SOURCES[symbol]
    return (f"<html><body>Issuer/ Manager {c['issuer']} Securities "
            f"{c['security_name']} - {c['isin']} - {symbol} "
            f"Date &amp;Time of Broadcast {c['broadcast']} "
            f"Announcement Reference {c['reference']}</body></html>").encode()

class Tests(unittest.TestCase):
    def test_both_banks_are_historical_only(self):
        for symbol in SOURCES:
            with self.subTest(symbol=symbol):
                rec=parse(symbol,fixture(symbol))
                self.assertEqual(rec["symbol"],symbol)
                self.assertFalse(rec["today_listing_status_verified"])
                self.assertFalse(rec["quote_or_current_shares_verified"])
                self.assertFalse(rec["eligible_for_market_cap_per_pbr"])
                self.assertFalse(rec["eligible_for_ranking"])
    def test_cross_bank_confusion_refused(self):
        with self.assertRaises(ValueError):parse("U11",fixture("O39"))
        with self.assertRaises(ValueError):parse("O39",fixture("U11"))
    def test_corruption_rejected(self):
        for symbol in SOURCES:
            for old,new in ((SOURCES[symbol]["isin"],"SG1FAKE00000"),
                            (SOURCES[symbol]["reference"],"SG260101FAKE"),
                            (SOURCES[symbol]["broadcast"],"01-Jan-2026 00:00:00")):
                with self.subTest(symbol=symbol,field=old),self.assertRaises(ValueError):
                    parse(symbol,fixture(symbol).replace(old.encode(),new.encode()))
    def test_duplicate_ticker_binding_refused(self):
        for symbol in SOURCES:
            c=SOURCES[symbol]
            extra=f" {c['security_name']} - {c['isin']} - {symbol}".encode()
            with self.assertRaises(ValueError):
                parse(symbol,fixture(symbol)+extra)
    def test_unavailable_html_fails_closed(self):
        with self.assertRaises(ValueError):parse("U11",b"<html>403 forbidden</html>"*20)
if __name__=="__main__":unittest.main()
