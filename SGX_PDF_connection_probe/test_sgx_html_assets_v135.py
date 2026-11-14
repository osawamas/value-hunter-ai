import unittest
from sgx_html_assets_v135 import analyze
class Tests(unittest.TestCase):
 def test_assets_are_leads_not_official_data(self):
  raw=b"""<html><script src="/static/main.js"></script>
  <link rel="stylesheet" href="/static/theme.css">
  <a href="/securities/stock-list.csv">Download</a>
  <script src="/static/main.js"></script></html>"""
  x=analyze(raw)
  self.assertEqual(x["javascript_resource_count"],1)
  self.assertEqual(x["potential_static_download_links"],1)
  self.assertFalse(x["downloadable_master_confirmed"])
  self.assertFalse(x["ranking_eligible"])
 def test_plain_skeleton_does_not_fabricate_endpoint(self):
  x=analyze(b"<html><body>Loading...</body></html>"*5)
  self.assertEqual(x["javascript_resource_count"],0)
  self.assertFalse(x["official_quote_endpoint_confirmed"])
 def test_tiny_document_rejected(self):
  with self.assertRaises(ValueError):analyze(b"")
if __name__=="__main__":unittest.main()
