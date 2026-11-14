import copy,unittest
from g13_primary_h1_reconcile_v127 import compare
from g13_shareholding_v48 import SOURCE
def fixture():
 h={"as_of_date":"2026-06-30","shares_outstanding":12063642274,
    "treasury_shares":30384550,"issued_shares_including_treasury":12094026824,
    "share_count_basis":"issued_excluding_treasury"}
 f={"schema_version":"value_hunter_web_v29","ranking_eligible_count":0,"records":[{
  "symbol":"G13","shares_as_of_date":"2026-06-30","shares_count_basis":"issued_excluding_treasury",
  "shares_source_url":SOURCE,"shares_outstanding":12063642274,
  "gross_issued_shares":12094026824,"treasury_shares":30384550,
  "shares_pdf_sha256":"a"*64}]}
 n={"schema_version":"sgx-g13-buyback-share-basis-v122","status":"SGX_G13_PRIMARY_JUNE10_BUYBACK_SHARE_SNAPSHOT",
    "record":{"symbol":"G13","purchase_date":"2026-06-10",
      "issued_excluding_treasury_after_purchase":12063642274,
      "treasury_shares_after_purchase":30384550,"june_30_shares_independently_confirmed":False,
      "source_url":"https://links.sgx.com/1.0.0/corporate-announcements/CHP29KEV0YJ4ZBNY/"}}
 return f,n,h,"a"*64
class Tests(unittest.TestCase):
 def test_june30_is_supported_by_own_original(self):
  f,n,h,s=fixture();prior=copy.deepcopy(f)
  o=compare(f,n,h,s)
  self.assertTrue(o["published_june30_count_original_primary_supported"])
  self.assertFalse(o["shares_after_june30_unchanged_verified"])
  self.assertFalse(o["ranking_eligible"])
  self.assertEqual(f,prior)
 def test_unsupported_provenance_refused(self):
  for change in [
   lambda f,n,h,s:f["records"][0].update(shares_as_of_date="2026-11-14"),
   lambda f,n,h,s:f["records"][0].update(shares_pdf_sha256="b"*64),
   lambda f,n,h,s:h.update(treasury_shares=1),
   lambda f,n,h,s:n["record"].update(june_30_shares_independently_confirmed=True),
   lambda f,n,h,s:f.update(ranking_eligible_count=1)]:
   f,n,h,s=fixture();change(f,n,h,s)
   with self.assertRaises(ValueError):compare(f,n,h,s)
if __name__=="__main__":unittest.main()
