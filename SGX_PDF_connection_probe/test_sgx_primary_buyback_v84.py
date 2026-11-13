"""v84: only issuer-matched original SGX Section D HTML can be considered.

Synthetic HTML tests assert fail-closed behavior; no live share promotion.
"""
import unittest
from sgx_primary_buyback_v84 import parse

URL="https://links.sgx.com/1.0.0/corporate-announcements/DAT1F106BZ1OENC5/"
REF="SG260930OTHRNN9Y"

def source(*,issuer="UNITED OVERSEAS BANK LIMITED",ref=REF,date="30/09/2026",
           count="1,647,838,591",treasury="14,548,000",repeated=False):
 parts=[
   "<h1>Share Buy Back - Daily Share Buy-Back Notice::Daily Share Buy-Back Notice</h1>",
   "<div>Issuer &amp; Securities</div><div>"+issuer+"</div>",
   "<div>Announcement Reference</div><div>"+ref+"</div>",
   "<div>Share Buy Back</div><div>Daily Share Buy-Back Notice</div>",
   "<section><h3>Section A</h3><p>Date of Purchase</p><p>"+date+"</p></section>",
   "<section><h3>Section D</h3>",
   "<p>Number of issued shares excluding treasury shares after purchase</p><p>"+count+"</p>",
   "<p>Number of treasury shares held after purchase</p><p>"+treasury+"</p>",
   "</section>"
 ]
 if repeated:
  parts.insert(-1,"<p>Number of issued shares excluding treasury shares after purchase</p><p>"+count+"</p>")
 return "<html><body>"+"".join(parts)+"</body></html>"

class PrimarySGXBuybackTests(unittest.TestCase):
 def test_direct_issuer_section_d_is_only_diagnostic(self):
  r=parse("U11",URL,source().encode(),REF,"2026-09-30")
  self.assertEqual(r["issued_excluding_treasury"],1647838591)
  self.assertEqual(r["treasury_shares"],14548000)
  self.assertEqual(r["issued_including_treasury_derived"],1662386591)
  self.assertTrue(r["not_proof_of_latest"])
  self.assertFalse(r["valuation_eligible"])
  self.assertFalse(r["ranking_eligible"])
 def test_secondary_source_refused(self):
  with self.assertRaises(ValueError):
   parse("U11","https://a.siasset.com/news/news.html?nid=515665417",
         source().encode(),REF,"2026-09-30")
 def test_unrelated_symbol_refused(self):
  with self.assertRaises(ValueError):parse("O39",URL,source().encode(),REF,"2026-09-30")
 def test_mismatched_reference_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL,source(ref="SG260929OTHRNN9Y").encode(),REF,"2026-09-30")
 def test_wrong_purchase_day_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL,source(date="29/09/2026").encode(),REF,"2026-09-30")
 def test_missing_section_d_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL,source().replace("Section D","Section C").encode(),REF,"2026-09-30")
 def test_ambiguous_duplicate_field_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL,source(repeated=True).encode(),REF,"2026-09-30")
 def test_invalid_negative_or_zero_shares_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL,source(count="0").encode(),REF,"2026-09-30")
 def test_redirect_or_query_url_refused(self):
  with self.assertRaises(ValueError):parse("U11",URL+"?fake=1",source().encode(),REF,"2026-09-30")
  with self.assertRaises(ValueError):parse("U11","https://links.sgx.com.evil.com/1.0.0/corporate-announcements/test/",source().encode(),REF,"2026-09-30")
 def test_text_in_script_not_considered(self):
  fake="<script>"+source()+"</script><p>No issued shares here</p>"
  with self.assertRaises(ValueError):parse("U11",URL,fake.encode(),REF,"2026-09-30")
if __name__=="__main__":unittest.main()
