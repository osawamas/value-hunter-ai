"""v102: API must preserve exact limit=200 URL and provider coverage evidence."""
import json,unittest
from sgx_companies_api_v98 import FETCH_URL,parse
from sgx_companies_publish_v99 import publish
from test_sgx_companies_api_v98 import sample
from test_sgx_companies_publish_v99 import verified

class APIExpandedTests(unittest.TestCase):
 def test_requested_limit_is_declared(self):
  self.assertEqual(FETCH_URL,"https://stocks.com.sg/api/v1/companies?limit=200")
  src=parse(sample())
  self.assertEqual(src["source_url"],FETCH_URL)
  out=publish(verified(),src)
  self.assertEqual(out["source_url"],FETCH_URL)
  self.assertEqual(out["provider_unaccepted_rows"],0)
  self.assertFalse(out["full_sgx_listing_completeness_verified"])
 def test_actual_provider_pagination_metadata_survives(self):
  src=json.loads(sample())
  src["meta"]={"count":62,"total":183,"limit":200,"offset":0,"next_offset":None}
  data=parse(json.dumps(src).encode())
  output=publish(verified(),data)
  self.assertEqual(output["provider_reported_total"],183)
  self.assertIsNone(output["provider_next_offset"])
  self.assertEqual(output["provider_accepted_candidate_count"],62)
  self.assertEqual(output["coverage"],"PARTIAL_UNVERIFIED")
 def test_one_invalid_record_kept_explicit(self):
  src=json.loads(sample())
  src["data"].append({"ticker":"INVALID-TICKER","company_name":"Bad entry"})
  src["meta"]={"total":len(src["data"]),"limit":200,"next_offset":None}
  output=publish(verified(),parse(json.dumps(src).encode()))
  self.assertEqual(output["provider_unaccepted_rows"],1)
  self.assertEqual(output["provider_accepted_candidate_count"],62)
if __name__=="__main__":unittest.main()
