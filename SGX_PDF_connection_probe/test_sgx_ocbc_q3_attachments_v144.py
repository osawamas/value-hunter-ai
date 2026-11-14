import hashlib,unittest
from sgx_ocbc_q3_attachments_v144 import discover
from sgx_ocbc_q3_original_v143 import ATTACHMENTS
def fixture():
 raw=("<html><body>"+"".join(f'<a href="/FileOpen/{name}">{name}</a>' for name in ATTACHMENTS)+"</body></html>").encode()
 return raw,{"status":"SGX_OCBC_2026Q3_PRIMARY_ANNOUNCEMENT_VERIFIED",
   "record":{"symbol":"O39","source_html_sha256":hashlib.sha256(raw).hexdigest()}}
class Tests(unittest.TestCase):
 def test_exact_official_attachments_only(self):
  raw,m=fixture();x=discover(raw,m)
  self.assertEqual(x["official_attachment_url_count"],3)
  self.assertFalse(x["downloaded_original_pdfs"])
  self.assertFalse(x["ranking_eligible"])
 def test_redirect_to_other_domain_does_not_pass(self):
  raw,m=fixture();raw=raw.replace(b'href="/FileOpen/',b'href="https://evil.test/FileOpen/')
  m["record"]["source_html_sha256"]=hashlib.sha256(raw).hexdigest()
  self.assertEqual(discover(raw,m)["official_attachment_url_count"],0)
 def test_unmatched_hash_fails(self):
  raw,m=fixture();m["record"]["source_html_sha256"]="f"*64
  with self.assertRaises(ValueError):discover(raw,m)
if __name__=="__main__":unittest.main()
