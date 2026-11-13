"""v53: stale or unanchored sources must never produce numeric valuations."""
import unittest
from datetime import datetime, timezone
from value_hunter_quality_v33 import audit_record

NOW=datetime(2026,11,14,tzinfo=timezone.utc)

def sample():
    price=1.2
    count=1_000_000
    return {
        "symbol":"TEST","ranking_eligible":False,
        "exclusion_reasons":["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"],
        "price_sgd":price,"shares_outstanding":count,
        "quote_timestamp_utc":"2026-11-13T04:00:00Z",
        "shares_as_of_date":"2026-10-01",
        "market_cap_sgd":price*count,
        "attributable_profit_sgd_thousands":100,
        "parent_equity_sgd_thousands":200,
        "per_reference":12,
        "pbr_reference_unverified":6,
        "pbr_verified":None,
    }

class FreshnessSuppressTests(unittest.TestCase):
    def test_recent_values_remain(self):
        r=audit_record(sample(),NOW)
        self.assertEqual(r["per_reference"],12)
        self.assertEqual(r["market_cap_sgd"],1_200_000)
        self.assertEqual(r["pbr_reference_unverified"],6)

    def test_old_quote_suppresses_derived(self):
        s=sample()
        s["quote_timestamp_utc"]="2026-10-01T00:00:00Z"
        r=audit_record(s,NOW)
        self.assertEqual(r["quote_freshness"],"STALE")
        for key in ("market_cap_sgd","per_reference","pbr_reference_unverified"):
            self.assertIsNone(r[key])
        self.assertNotIn("MARKET_CAP_ARITHMETIC_MISMATCH",r["quality_flags"])
        self.assertIn("VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE",r["exclusion_reasons"])

    def test_old_shares_suppresses(self):
        s=sample()
        s["shares_as_of_date"]="2025-01-01"
        r=audit_record(s,NOW)
        self.assertEqual(r["share_freshness"],"STALE")
        self.assertIsNone(r["market_cap_sgd"])

    def test_missing_quote_date_suppresses(self):
        s=sample()
        s["quote_timestamp_utc"]=None
        r=audit_record(s,NOW)
        self.assertIsNone(r["market_cap_sgd"])

    def test_future_share_date_suppresses(self):
        s=sample()
        s["shares_as_of_date"]="2027-01-01"
        r=audit_record(s,NOW)
        self.assertIsNone(r["per_reference"])

if __name__=="__main__":unittest.main()
