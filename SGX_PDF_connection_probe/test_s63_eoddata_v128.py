import unittest
from s63_eoddata_v128 import parse

def fixture():
 return ("""<html><h1>SGX, S63: ST Engineering</h1>
 <div>13 Nov 2026 LAST: 9.670 CHANGE 0.090</div>
 <h2>RECENT END OF DAY PRICES</h2><table><tr>
 <td>13 Nov 26</td><td>9.660</td><td>9.770</td>
 <td>9.470</td><td>9.670</td><td>5.29M</td>
 </tr></table></html>""").encode()
class Tests(unittest.TestCase):
 def test_research_only(self):
  x=parse(fixture())
  self.assertEqual(x["close_sgd_research"],9.67)
  self.assertFalse(x["upstream_market_data_independence_verified"])
  self.assertFalse(x["ranking_eligible"])
 def test_wrong_date_or_ticker(self):
  for old,new in ((b"SGX, S63",b"SGX, U11"),
                  (b"13 Nov 2026",b"12 Nov 2026"),
                  (b"13 Nov 26",b"12 Nov 26"),
                  (b"9.670",b"9.770")):
   with self.subTest(old=old),self.assertRaises(ValueError):
    parse(fixture().replace(old,new))
 def test_duplicate_historical_row(self):
  with self.assertRaises(ValueError):parse(fixture()+b"13 Nov 26 9.660 9.770 9.470 9.670 5.29M")
if __name__=="__main__":unittest.main()
