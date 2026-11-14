import unittest
from sgx_boardlot_subset_v142 import parse,EXPECTED
def fixture():
 tr="".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"%(v[0],k,v[1]) for k,v in EXPECTED.items())
 return ('<html><body>5 October 2026: securities with reduced board lot<table>'+tr+'</table></body></html>').encode()
class Tests(unittest.TestCase):
 def test_official_historical_subset_not_full_master(self):
  x=parse(fixture())
  self.assertEqual(x["official_historical_ticker_count"],11)
  self.assertFalse(x["subset_is_complete_current_sgx_master"])
  self.assertFalse(x["listing_active_as_of_today_confirmed"])
 def test_missing_code_fails(self):
  with self.assertRaises(ValueError):parse(fixture().replace(b"<td>U11</td>",b"<td>XX1</td>"))
 def test_changed_currency_fails(self):
  with self.assertRaises(ValueError):parse(fixture().replace(b"<td>J36</td><td>USD",b"<td>J36</td><td>SGD"))
if __name__=="__main__":unittest.main()
