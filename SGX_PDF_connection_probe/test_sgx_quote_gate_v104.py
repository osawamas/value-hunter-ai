"""v104: adversarial offline price validation with pinned simulated clock."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sgx_quote_gate_v104 import validate_quote, run, SECURITIES, CANDIDATE_SOURCE

NOW=datetime(2026,11,14,2,0,tzinfo=timezone.utc)
URL="https://www.sgx.com/securities/securities-prices?code=stocks"

def fixture(symbol="U11"):
    return {"symbol":symbol,"isin":SECURITIES[symbol]["isin"],"currency":"SGD",
            "exchange":"XSES","price":37.75,"as_of":"2026-11-13T17:16+08:00",
            "source_url":URL,"source_kind":CANDIDATE_SOURCE}

class QuoteGateTests(unittest.TestCase):
    def test_research_only(self):
        for symbol in SECURITIES:
            x=validate_quote(fixture(symbol),now=NOW)
            self.assertTrue(x["identity_and_timestamp_checked"])
            self.assertFalse(x["eligible_for_market_cap"])
            self.assertFalse(x["eligible_for_per_pbr"])
            self.assertFalse(x["eligible_for_ranking"])
            self.assertFalse(x["actual_quote_from_sgx_verified"])
    def assert_bad(self, **changes):
        x=fixture()
        x.update(changes)
        with self.assertRaises(ValueError):
            validate_quote(x,now=NOW)
    def test_incorrect_identity(self):
        self.assert_bad(symbol="D05")
        self.assert_bad(isin="SG1FAKE")
        self.assert_bad(currency="USD")
        self.assert_bad(exchange="NYSE")
    def test_missing_or_wrong_time(self):
        self.assert_bad(as_of="2026-11-13T17:16")
        self.assert_bad(as_of="2026-11-13T17:16Z")
        self.assert_bad(as_of="2026-11-14T12:16+08:00")
        self.assert_bad(as_of="2026-11-01T17:16+08:00")
        self.assert_bad(as_of="2026-11-13T22:16+08:00")
    def test_price_and_source(self):
        for price in (0,-1,float("nan"),float("inf"),"37.75",True):
            self.assert_bad(price=price)
        self.assert_bad(source_url="https://evil.example/quote")
        self.assert_bad(source_kind="THIRD_PARTY")
    def test_extra_field_rejected(self):
        self.assert_bad(per=5)
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"input.json"; b=Path(d)/"out.json"
            a.write_text(json.dumps({"quotes":[fixture(),fixture()],
                   "source_retrieved_at":NOW.isoformat()}))
            with self.assertRaises(ValueError):
                run(a,b)
            self.assertFalse(b.exists())
    def test_no_synthetic_live_quote_fabrication(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"input.json";b=Path(d)/"out.json"
            a.write_text(json.dumps({"quotes":[],
                   "source_retrieved_at":NOW.isoformat()}))
            got=run(a,b)
            self.assertEqual(got["quote_count"],0)
            self.assertFalse(got["feed_promotion_allowed"])
            self.assertFalse(got["ranking_allowed"])
            self.assertTrue(b.exists())

if __name__=="__main__":
    unittest.main()
