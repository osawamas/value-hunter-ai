import unittest
from sgx_ocbc_q3_pdfs_v145 import audit
class Tests(unittest.TestCase):
 def test_missing_authenticated_links_fails(self):
  with self.assertRaises(ValueError):audit({"status":"NOT_VERIFIED"},lambda url:b"")
 def test_non_pdf_rejected(self):
  m={"status":"SGX_OCBC_Q3_ATTACHMENT_LINKS_RESEARCHED",
     "record":{"schema_version":"sgx-ocbc-q3-official-attachment-links-v144",
      "all_three_verified_attachment_links":True,
      "attachments":[{"filename":name,"unique_direct_sgx_link":True,
        "resolved_official_link":"https://links.sgx.com/"+name} for name in
         ("OCBC_3Q26_Results_Press_Release.pdf","OCBC_3Q26_CEO_Presentation.pdf","OCBC_3Q26_Results_Highlights.pdf")]}}
  with self.assertRaises(ValueError):audit(m,lambda url:b"<html>fake PDF</html>")
if __name__=="__main__":unittest.main()
