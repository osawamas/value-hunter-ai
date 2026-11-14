"""v105 negative fixtures: no falsely official SGX listing claims."""
import hashlib
import json
import unittest
from datetime import datetime, timezone
from sgx_master_reconcile_v105 import reconcile, OFFICIAL_URL

def candidates():
    return {
        "schema_version": "sgx-third-party-company-candidates-v99",
        "source_json_sha256": "a"*64, "coverage":"PARTIAL_UNVERIFIED",
        "full_sgx_listing_completeness_verified": False, "eligible_for_ranking":False,
        "candidates":[{"symbol":f"A{i:02d}","financial_verification":False,
                        "ranking_eligible":False} for i in range(25)]
    }

def official():
    return ("trading_code,isin,trading_name,market_board,security_type\n"+
            "A00,SG1L01001701,Example Zero,Mainboard,Stock\n"+
            "ZZ9,SG1S04926220,Outside Candidate,Catalist,Stock\n").encode()

def provenance(raw):
    t=datetime.now(timezone.utc).isoformat()
    return {"source_url":OFFICIAL_URL,"retrieved_utc":t,"document_date":t[:10],
            "sha256":hashlib.sha256(raw).hexdigest(),
            "capture_method":"DIRECT_SGX_DOWNLOAD","exchange_origin_verified":True}

class MasterTests(unittest.TestCase):
    def test_no_master_means_no_matches(self):
        x=reconcile(candidates())
        self.assertEqual(x["official_master_status"],"NOT_AVAILABLE")
        self.assertEqual(x["official_confirmed_candidate_count"],0)
        self.assertEqual(len(x["candidate_symbols_without_official_match"]),25)
        self.assertFalse(x["official_master_completeness_verified"])
        self.assertFalse(x["ranking_eligible"])
    def test_independent_master_always_still_incomplete(self):
        raw=official();x=reconcile(candidates(),raw,provenance(raw))
        self.assertEqual(x["official_confirmed_candidate_count"],1)
        self.assertEqual(x["official_symbols_outside_candidate_index"],["ZZ9"])
        self.assertEqual(len(x["candidate_symbols_without_official_match"]),24)
        self.assertFalse(x["official_master_completeness_verified"])
        self.assertFalse(x["ranking_eligible"])
    def test_reject_bad_provenance(self):
        raw=official();p=provenance(raw)
        for k,v in [("sha256","0"*64),("source_url","https://example.test"),
                    ("capture_method","THIRD_PARTY"),("exchange_origin_verified",False),
                    ("document_date","not-a-date")]:
            bad=dict(p);bad[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):
                reconcile(candidates(),raw,bad)
    def test_no_candidate_self_promotion(self):
        x=candidates();x["eligible_for_ranking"]=True
        with self.assertRaises(ValueError):reconcile(x)
        x=candidates();x["candidates"][0]["financial_verification"]=True
        with self.assertRaises(ValueError):reconcile(x)
    def test_duplicate_exchange_ticker_fails(self):
        raw=official()+b"A00,SG1L01001701,Again,Mainboard,Stock\n"
        with self.assertRaises(ValueError):
            reconcile(candidates(),raw,provenance(raw))

if __name__=="__main__":
    unittest.main()
