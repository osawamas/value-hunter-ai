import unittest
from uob_ir_nov13_v163 import analyze
class Tests(unittest.TestCase):
 def test_issuer_host_not_sgx_original(self):
  html=b"<html><body><h2>Daily Share Buy-Back Notice</h2>13 Nov 2026 SG261113OTHRHOAF <a href='https://links.sgx.com/1.0.0/link'>SGX</a></body></html>"
  r=analyze(html)
  self.assertTrue(r["UOB_ir_announcement_identity_verified"])
  self.assertFalse(r["sgx_original_announcement_verified"])
  self.assertIsNone(r["uob_treasury_adjusted_shares_from_primary_sgx"])
 def test_missing_reference_not_confirmed(self):
  r=analyze(b"<html><body>Daily Share Buy-Back Notice 13 Nov 2026</body></html>"*2)
  self.assertFalse(r["UOB_ir_announcement_identity_verified"])
if __name__=="__main__":unittest.main()
