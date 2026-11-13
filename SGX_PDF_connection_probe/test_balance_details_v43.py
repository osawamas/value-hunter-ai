import unittest
from datetime import datetime, timezone

from value_hunter_v28 import evaluate
from value_hunter_web_v29 import build


class BalanceDetailsTests(unittest.TestCase):
    def test_g13_source_balances_and_pbr_denominator(self):
        fin = {"symbol":"G13", "fiscal_year":2025,
               "source_url":"https://links.sgx.com/annual.pdf",
               "g13_balance_evidence":{"status":"EXTRACTED_GROUP_BALANCE_ARITHMETIC_MATCHED",
                                       "page_pdf_number":62},
               "metrics":{
                 "revenue":{"2025":{"value":2452053}},
                 "attributable_profit":{"2025":{"value":390346}},
                 "operating_profit":{"2025":{"value":506609}},
                 "assets":{"2025":{"value":9185799}},
                 "liabilities":{"2025":{"value":980383}},
                 "equity":{"2025":{"value":8205416}}
               }}
        val = {"symbol":"G13",
               "quote":{"price_sgd":0.575,
                        "market_timestamp_utc":"2026-11-13T09:13:51Z"},
               "shares":{"shares_outstanding":12063642274,
                         "as_of_date":"2026-08-14",
                         "source_url":"https://example.org/shares"},
               "parent_equity_sgd_thousands":8205416,
               "parent_equity_status":"GROUP_ORDINARY_SHAREHOLDER_EQUITY_SAME_ISSUER_PDF",
               "parent_equity_source":"https://links.sgx.com/annual.pdf"}
        now=datetime(2026,11,14,tzinfo=timezone.utc)
        rec=evaluate(fin,val,{"symbol":"G13","checks":[]},now)
        self.assertEqual(rec["assets_sgd_thousands"],9185799)
        self.assertEqual(rec["liabilities_sgd_thousands"],980383)
        self.assertEqual(rec["equity_sgd_thousands"],8205416)
        self.assertEqual(rec["balance_difference_sgd_thousands"],0)
        self.assertEqual(rec["balance_source_page"],62)
        self.assertEqual(rec["parent_equity_sgd_thousands"],8205416)
        self.assertEqual(rec["pbr_reference_unverified"],0.8454)
        self.assertIsNone(rec["pbr_verified"])
        self.assertFalse(rec["ranking_eligible"])

    def test_public_feed_keeps_null_and_scope(self):
        records = []
        for sym in ("S68","G13","S20"):
            records.append({
                "symbol":sym,"ranking_eligible":False,
                "exclusion_reasons":["INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE"],
                "assets_sgd_thousands":9185799 if sym=="G13" else None,
                "liabilities_sgd_thousands":980383 if sym=="G13" else None,
                "equity_sgd_thousands":8205416 if sym=="G13" else None,
                "balance_source_status":"EXTRACTED_GROUP_BALANCE_ARITHMETIC_MATCHED" if sym=="G13" else None,
                "parent_equity_sgd_thousands":8205416 if sym=="G13" else None,
                "parent_equity_source_url":"https://links.sgx.com/annual.pdf" if sym=="G13" else None,
            })
        result=build({"schema_version":"value_hunter_sgx_v28","records":records})
        items={r["symbol"]:r for r in result["records"]}
        self.assertEqual(items["G13"]["assets_sgd_thousands"],9185799)
        self.assertEqual(items["G13"]["parent_equity_sgd_thousands"],8205416)
        self.assertIsNone(items["S20"]["assets_sgd_thousands"])
        self.assertFalse(result["ranking_enabled"])


if __name__=="__main__":
    unittest.main()
