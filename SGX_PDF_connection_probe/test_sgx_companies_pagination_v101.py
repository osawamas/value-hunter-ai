"""v101: pagination parameter differences must not imply SGX completeness."""
import json,unittest
from sgx_companies_pagination_v101 import diagnose
from test_sgx_companies_api_v98 import sample

def call_distinct(query):
 d=json.loads(sample())
 for rec in d["data"]:
  if query.get("page")=="2":
   rec["ticker"]="Y"+rec["ticker"][1:]
  elif query.get("limit")=="200":
   rec["ticker"]="Z"+rec["ticker"][1:]
 return json.dumps(d).encode()

class Tests(unittest.TestCase):
 def test_three_queries_distinct(self):
  d=diagnose(call_distinct)
  self.assertEqual(d["request_count"],3)
  self.assertTrue(d["page2_delivers_new_symbols"])
  self.assertTrue(d["larger_limit_delivers_new_symbols"])
  self.assertFalse(d["complete_sgx_universe_verified"])
  self.assertFalse(d["candidate_market_valuation_eligible"])
 def test_ignored_parameters_detected(self):
  d=diagnose(lambda _:sample())
  self.assertFalse(d["page2_delivers_new_symbols"])
  self.assertFalse(d["larger_limit_delivers_new_symbols"])
 def test_fetch_error_is_not_silent(self):
  def call(p):
   if p.get("page")=="2":raise RuntimeError("429")
   return sample()
  d=diagnose(call)
  self.assertEqual(d["snapshots"][1]["status"],"NOT_VERIFIED")
  self.assertIn("429",d["snapshots"][1]["error"])
  self.assertFalse(d["complete_sgx_universe_verified"])
if __name__=="__main__":unittest.main()
