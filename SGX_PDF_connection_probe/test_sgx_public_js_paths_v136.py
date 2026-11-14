import unittest
from sgx_public_js_paths_v136 import parse
URL="https://www.sgx.com/securities/index.32e3899753ae86309a56.chunk.js"
class Tests(unittest.TestCase):
 def test_public_paths_only_not_api_confirmation(self):
  raw=b'const a="https://api.sgx.com/v1/markets/stock-data?key=secret";const b="/api/marketdata/getPrices";'
  out=parse(raw,URL)
  self.assertIn("api.sgx.com/v1/markets/stock-data",out["official_domain_literal_paths"])
  self.assertNotIn("secret",str(out))
  self.assertFalse(out["official_json_api_confirmed"])
  self.assertFalse(out["quote_verified"])
 def test_other_domain_not_presumed_sgx(self):
  raw=b'const a="https://example.com/private/token";const b="some securities stockcode";'
  out=parse(raw,URL)
  self.assertEqual(out["official_domain_literal_paths"],[])
 def test_bad_script_source_refused(self):
  with self.assertRaises(ValueError):parse(b"const quote = 123;"*6,"https://evil.example/quote.js")
if __name__=="__main__":unittest.main()
