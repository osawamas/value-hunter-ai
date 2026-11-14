import unittest
from sgx_ocbc_q3_original_v143 import parse,ATTACHMENTS
def fixture():
 return ("""<html><body>
 Issuer/ Manager OVERSEA-CHINESE BANKING CORPORATION LIMITED
 Securities OVERSEA-CHINESE BANKING CORP - SG1S04926220 - O39
 Financial Statements and Related Announcement
 Date &amp;Time of Broadcast 06-Nov-2026 06:59:27
 Announcement Sub Title Third Quarter Results
 Announcement Reference SG261106OTHRI4L9
 For Financial Period Ended 30/09/2026
 Attachments """+" ".join(ATTACHMENTS)+"</body></html>").encode()
class Tests(unittest.TestCase):
 def test_manifest_not_numerical_verification(self):
  x=parse(fixture())
  self.assertEqual(x["symbol"],"O39")
  self.assertFalse(x["attached_pdfs_downloaded_and_numerically_parsed"])
  self.assertFalse(x["ranking_eligible"])
 def test_bad_primary_fields(self):
  for a,b in [(b"SG1S04926220",b"FAKE"),(b"06:59:27",b"06:59:28"),
              (b"SG261106OTHRI4L9",b"FAKE"),
              (b"30/09/2026",b"30/06/2026")]:
   with self.subTest(a=a),self.assertRaises(ValueError):
    parse(fixture().replace(a,b))
 def test_missing_attachment(self):
  with self.assertRaises(ValueError):parse(fixture().replace(ATTACHMENTS[0].encode(),b"missing.pdf"))
if __name__=="__main__":unittest.main()
