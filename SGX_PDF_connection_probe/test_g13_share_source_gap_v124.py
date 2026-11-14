import unittest
from g13_share_source_gap_v124 import compare
def docs():
 f={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,
   "records":[{"symbol":"G13","shares_count_basis":"issued_excluding_treasury",
    "shares_outstanding":12063642274,"shares_as_of_date":"2026-06-30"}]}
 r={"status":"SGX_G13_PRIMARY_JUNE10_BUYBACK_SHARE_SNAPSHOT",
    "symbol":"G13","isin":"SGXE21576413","reference":"SG260610OTHRU53S",
    "purchase_date":"2026-06-10","proof_applies_only_to_june_10":True,
    "june_30_shares_independently_confirmed":False,"current_shares_verified":False,
    "ranking_eligible":False,"source_url":"https://links.sgx.com/1.0.0/corporate-announcements/CHP29KEV0YJ4ZBNY/",
    "issued_excluding_treasury_after_purchase":12063642274,"html_sha256":"a"*64}
 return f,{"schema_version":"sgx-g13-buyback-share-basis-v122",
  "status":r["status"],"source_url":r["source_url"],"record":r}
class Tests(unittest.TestCase):
 def test_same_shares_different_date_is_not_official_certification(self):
  x=compare(*docs())
  self.assertEqual(x["date_difference_days"],20)
  self.assertTrue(x["quantity_matched"])
  self.assertFalse(x["primary_source_proves_published_date"])
  self.assertFalse(x["ranking_eligible"])
 def test_forged_status(self):
  a,b=docs();b["record"]["june_30_shares_independently_confirmed"]=True
  with self.assertRaises(ValueError):compare(a,b)
 def test_wrong_basis(self):
  a,b=docs();a["records"][0]["shares_count_basis"]="gross"
  with self.assertRaises(ValueError):compare(a,b)
 def test_quantity_disagreement_is_reported(self):
  a,b=docs();a["records"][0]["shares_outstanding"]=12063000000
  self.assertFalse(compare(a,b)["quantity_matched"])
if __name__=="__main__":unittest.main()
