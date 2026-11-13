import unittest
from value_hunter_web_v29 import build

class ShareProvenancePublication(unittest.TestCase):
    def test_public_feed_exposes_reconciled_share_provenance(self):
        rows=[]
        for sym in ("S68","G13","S20"):
            r={"symbol":sym,"ranking_eligible":False,
               "exclusion_reasons":["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"]}
            if sym=="S68":
                r.update(shares_outstanding=1070843484,
                         gross_issued_shares=1071642400,
                         treasury_shares=798916,
                         shares_count_basis="issued_excluding_treasury",
                         shares_pdf_sha256="a"*64,
                         shares_verification_status="LIVE_OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED")
            rows.append(r)
        published=build({"schema_version":"value_hunter_sgx_v28","records":rows})
        by={x["symbol"]:x for x in published["records"]}
        s=by["S68"]
        self.assertEqual(s["gross_issued_shares"]-s["treasury_shares"],s["shares_outstanding"])
        self.assertEqual(s["shares_pdf_sha256"],"a"*64)
        self.assertIsNone(by["G13"]["shares_pdf_sha256"])
        self.assertFalse(published["ranking_enabled"])

if __name__=="__main__":
    unittest.main()
