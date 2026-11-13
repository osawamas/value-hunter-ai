import copy
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from sgx_universe_v30 import validate_universe, read_universe
from value_hunter_v28 import compare
from value_hunter_web_v29 import build

def issuer(symbol):
    return {
        "symbol": symbol, "issuer": "Company " + symbol,
        "financial_pdf_url": "https://example.org/" + symbol + ".pdf",
        "market": "SGX", "currency": "SGD", "financial_reference_year": 2025,
        "financial_data_status": "NOT_YET_PARSED",
    }

def universe(symbols=("S68", "G13", "S20")):
    return {"schema_version": "sgx_issuer_universe_v30",
            "issuers": [issuer(s) for s in symbols]}

class UniverseTests(unittest.TestCase):
    def test_catalog_has_seven_source_backed_issuers(self):
        path = Path(__file__).with_name("sgx_universe_v30.json")
        rows = read_universe(path)
        self.assertEqual([r["symbol"] for r in rows], ["S68", "G13", "S20", "S63", "D05", "O39", "U11"])

    def test_new_banks_have_no_parsed_metrics_or_auto_ranking(self):
        catalog=json.loads(Path(__file__).with_name("sgx_universe_v30.json").read_text(encoding="utf-8"))
        result=compare({"records":[]},{"records":[]},{"records":[]},
                       now=datetime(2026,11,14,tzinfo=timezone.utc),universe=catalog)
        banks=[r for r in result["records"] if r["symbol"] in {"D05","O39","U11"}]
        self.assertEqual(len(banks),3)
        for record in banks:
            self.assertIsNone(record["price_sgd"])
            self.assertIsNone(record["per_reference"])
            self.assertIsNone(record["pbr_reference_unverified"])
            self.assertIsNone(record["market_cap_sgd"])
            self.assertFalse(record["ranking_eligible"])
            self.assertIn("FINANCIAL_MISSING_REVENUE",record["exclusion_reasons"])
        published=build(result,datetime(2026,11,14,tzinfo=timezone.utc))
        self.assertEqual(published["coverage"]["registered_count"],7)
        self.assertFalse(published["coverage"]["all_sgx_listed"])

    def test_duplicate_rejected(self):
        u = universe(("S68", "S68"))
        with self.assertRaises(ValueError):
            validate_universe(u)

    def test_reject_unproven_source(self):
        u = universe()
        u["issuers"][0]["financial_pdf_url"] = "http://example.org/a.pdf"
        with self.assertRaises(ValueError):
            validate_universe(u)

    def test_reject_other_market(self):
        u = universe()
        u["issuers"][0]["market"] = "NYSE"
        with self.assertRaises(ValueError):
            validate_universe(u)

    def test_empty_catalog_rejected(self):
        with self.assertRaises(ValueError):
            validate_universe(universe(()))

    def test_new_registered_issuer_is_no_data_not_fabricated(self):
        u = universe(("S68", "G13", "S20", "X99"))
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        comparison = compare({"records": []}, {"records": []}, {"records": []},
                             now=now, universe=u)
        self.assertEqual(len(comparison["records"]), 4)
        row = comparison["records"][-1]
        self.assertEqual(row["symbol"], "X99")
        self.assertIsNone(row["market_cap_sgd"])
        self.assertIsNone(row["price_sgd"])
        self.assertFalse(row["ranking_eligible"])
        self.assertIn("FINANCIAL_MISSING_REVENUE", row["exclusion_reasons"])
        published = build(comparison, now)
        self.assertEqual(len(published["records"]), 4)
        self.assertEqual(published["records"][-1]["issuer"], "Company X99")
        self.assertFalse(published["coverage"]["all_sgx_listed"])

    def test_missing_declared_symbol_is_rejected(self):
        u = universe(("S68", "G13", "S20", "X99"))
        comparison = compare({"records":[]}, {"records":[]}, {"records":[]},
                             universe=u)
        comparison["records"].pop()
        with self.assertRaises(ValueError):
            build(comparison)

    def test_unverified_promotion_rejected(self):
        comparison = compare({"records":[]}, {"records":[]}, {"records":[]},
                             universe=universe(("S68","G13","S20","X99")))
        comparison["records"][-1]["ranking_eligible"] = True
        with self.assertRaises(ValueError):
            build(comparison)

if __name__ == "__main__":
    unittest.main()
