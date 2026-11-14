"""SGX individual issuer evidence is non-promotional even when matched."""
import unittest
from sgx_issuer_page_v106 import parse, EXPECTED_NAME, EXPECTED_ISIN

def fixture(name=EXPECTED_NAME,isin=EXPECTED_ISIN,board="MAINBOARD",time="11/11/2026 08:45:30 AM"):
    return (f"<html><body><h2>Basic Info</h2><h2>{name}</h2>"
            f"<p>Full Company Name : {name}</p>"
            f"<p>ISIN Code : {isin}</p>"
            f"<p>LISTING Listed on 23 November 2000 on SGX Mainboard</p>"
            f"<p>LISTING BOARD {board}</p>"
            f"<p>Information last updated on {time}</p></body></html>").encode()

class IssuerPageTests(unittest.TestCase):
    def test_verified_identity_does_not_verify_counter(self):
        r=parse(fixture())
        self.assertEqual(r["isin"], EXPECTED_ISIN)
        self.assertFalse(r["symbol_directly_observed_on_sgx_page"])
        self.assertFalse(r["symbol_to_isin_official_master_join_verified"])
        self.assertFalse(r["eligible_for_ranking"])
    def test_wrong_issuer_refused(self):
        for raw in (fixture(name="NOT SGX LTD"),fixture(isin="SG1L01001701"),
                    fixture(board="CATALIST"),fixture(time="NO DATE"),
                    fixture()+b" ISIN Code : SG1M31001969 "):
            with self.subTest(raw=raw[-50:]),self.assertRaises(ValueError):
                parse(raw)
    def test_error_pages_refused(self):
        with self.assertRaises(ValueError):
            parse(b"<html>Access denied</html>"*20)
if __name__=="__main__":unittest.main()
