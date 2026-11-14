"""v98: keyless SGX company index is secondary and may be incomplete."""
import json,unittest
from sgx_companies_api_v98 import parse

def sample(*,duplicates=False,partial=False,missing_symbols=False):
 codes=["S68","G13","S20","S63","D05","O39","U11"]+[f"X{i:03d}" for i in range(55)]
 if partial:codes=codes[:10]
 if missing_symbols:codes.remove("U11")
 rows=[{"ticker":code,"company_name":code+" Holdings Limited","gics_sector":"Financials"}
       for code in codes]
 if duplicates:rows.append({"ticker":"U11","company_name":"Wrong UOB"})
 return json.dumps({"data":rows,"meta":{"count":len(rows)}}).encode()

class TestAPI(unittest.TestCase):
 def test_candidate_index_is_not_investable(self):
  item=parse(sample())
  self.assertEqual(item["accepted_candidates"],62)
  self.assertTrue(item["all_7_known_present"])
  self.assertEqual(item["known_symbols_missing"],[])
  self.assertFalse(item["all_sgx_listings_verified"])
  self.assertFalse(item["ranking_eligible"])
  self.assertFalse(item["current_market_price_verified"])
  self.assertEqual(len(item["source_response_sha256"]),64)
 def test_duplicate_ticker_fails(self):
  with self.assertRaises(ValueError):parse(sample(duplicates=True))
 def test_small_coverage_fails(self):
  with self.assertRaises(ValueError):parse(sample(partial=True))
 def test_missing_original_7_not_concealed(self):
  item=parse(sample(missing_symbols=True))
  self.assertIn("U11",item["known_symbols_missing"])
  self.assertFalse(item["all_7_known_present"])
 def test_html_or_error_fails(self):
  for raw in (b"<html>403</html>",b'{"error":"no access"}'):
   with self.assertRaises((ValueError,json.JSONDecodeError)):parse(raw)
 def test_nonnumeric_ticker_rejected(self):
  obj=json.loads(sample())
  obj["data"][8]["ticker"]="../bad"
  item=parse(json.dumps(obj).encode())
  self.assertEqual(item["rejected_rows_count"],1)
  self.assertEqual(item["accepted_candidates"],61)
if __name__=="__main__":unittest.main()
