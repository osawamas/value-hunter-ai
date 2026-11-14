"""v97: universe discovery is a candidate directory, not verified SGX listing."""
import unittest
from sgx_universe_candidates_v97 import parse,KNOWN

def fixture(*,duplicate=False,missing=False,sparse=False):
 codes=list(KNOWN)+[f"X{i:03d}" for i in range(125)]
 if missing:codes.remove("U11")
 if sparse:codes=codes[:9]
 links=[f'<li><a href="/sgx/stock/{code.lower()}">{code} HOLDINGS LIMITED (SGX: {code})</a></li>'
        for code in codes]
 if duplicate:links.append('<a href="/sgx/stock/u11">Another Bank (SGX: U11)</a>')
 return ('<html><title>SGX Listed Companies</title><body><h1>SGX Listed Companies</h1>'+
         "".join(links)+'</body></html>').encode()

class TestUniverse(unittest.TestCase):
 def test_many_candidates_not_ranked(self):
  r=parse(fixture())
  self.assertEqual(r["candidate_count"],132)
  self.assertEqual(r["status"],"SECONDARY_SGX_UNIVERSE_CANDIDATES_DIAGNOSTIC_ONLY")
  self.assertTrue(r["known_7_present"])
  self.assertTrue(r["authoritative_sgx_listing_completeness_unverified"])
  self.assertTrue(r["candidate_not_verified_issuer_registry"])
  self.assertFalse(r["ranking_eligible"])
  self.assertEqual(len(r["raw_html_sha256"]),64)
  self.assertIn("O39",[x["symbol"] for x in r["stock_tickers"]])
 def test_duplicate_same_symbol_rejected(self):
  with self.assertRaises(ValueError):parse(fixture(duplicate=True))
 def test_missing_one_known_symbol_rejected(self):
  with self.assertRaises(ValueError):parse(fixture(missing=True))
 def test_tiny_partial_directory_rejected(self):
  with self.assertRaises(ValueError):parse(fixture(sparse=True))
 def test_wrong_directory_rejected(self):
  with self.assertRaises(ValueError):parse(b"<html>some unrelated page</html>")
 def test_malicious_markup_non_whitelisted_ticker_ignored(self):
  body=fixture().decode().replace("</body>","<a>Malformed (SGX: ../BAD)</a></body>")
  r=parse(body.encode())
  self.assertEqual(r["candidate_count"],132)

if __name__=="__main__":unittest.main()
