"""Exercise the compiled offline replay with the saved audit and a complete input pair."""

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLASSPATH = sys.argv.pop(1) if __name__ == "__main__" else None
PRIOR = "2026-11-16"
DAY = "2026-11-17"
ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(CLASSPATH, "Pass the compiled replay classpath when running directly")
class DatedReplayTests(unittest.TestCase):
    def replay(self, audit, *inputs):
        return subprocess.check_output([
            "java", "-cp", CLASSPATH, "jp.valuehunter.privatewatch.UsDatedRetryReplay", audit, *inputs
        ], text=True)

    def test_saved_audit_replays_all_reasons_with_no_unproven_admissions(self):
        audit = ROOT / "docs/us-dated-listing-audit-20261117.json"
        output = self.replay(audit)
        self.assertEqual(output, self.replay(audit))
        report = json.loads(output)
        self.assertEqual(report["audited_symbols"], 24)
        self.assertEqual(report["increase"], {"closes": 0, "screened": 0, "alert_candidates": 0})
        self.assertEqual(Counter(report["held"].values()), {
            "exact_dated_listing_pair_unavailable": 18,
            "standalone_share_evidence_pending": 2,
            "class_specific_financials_pending": 2,
            "split_basis_and_class_specific_shares_pending": 1,
        })
        self.assertEqual(list(report["excluded"]), ["MXE"])

    def test_exact_pair_adds_one_candidate_once_and_leaves_changed_class_on_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def write(name, contents):
                file = root / name
                file.write_text(json.dumps(contents), encoding="utf-8")
                return file

            def response(rows):
                return {"query_execution_status": "Success", "rows": rows}

            def close(symbol, session, price):
                return {"symbol": symbol, "trading_date": session, "close": price}

            def fact(value, end, **extra):
                return {"filed": "2026-10-20", "accn": "0000012345-26-000001",
                        "form": "10-K", "val": value, "end": end, **extra}

            audit = write("audit.json", {"trading_date_et": DAY, "comparison_date_et": PRIOR, "rows": [
                {"symbol": symbol, "disposition": "held", "exchange": "NYSE", "cik": cik,
                 "primary_reason": "exact_dated_listing_pair_unavailable"}
                for symbol, cik in [("FIX", 12345), ("CHANGE", 43210)]
            ]})
            for session, stamp, share_class in [(PRIOR, "11162026", "A"), (DAY, "11172026", "B")]:
                (root / f"{session}-nyse.txt").write_text(
                    "ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
                    "FIX|Repair Corp Common Stock|N|N|N\n"
                    f"CHANGE|Change Corp Class {share_class} Common Stock|N|N|N\n"
                    f"File Creation Time: {stamp}16:08||||\n", encoding="utf-8")
                (root / f"{session}-nasdaq.txt").write_text(
                    "Symbol|Security Name|NextShares|ETF|Test Issue\n"
                    "AAA|Other Corp Common Stock|N|N|N\n"
                    f"File Creation Time: {stamp}16:08||||\n", encoding="utf-8")

            write("closes.json", response([close("FIX", PRIOR, 20)]))
            write("supplement.json", response([close("FIX", DAY, 5), close("CHANGE", DAY, 5)]))
            write("splits.json", response([{"symbol": "FIX", "split_date": "2026-11-18"}]))
            write("fx.json", [{"date": session, "base": "USD", "quote": "JPY", "rate": 150}
                              for session in [PRIOR, DAY]])
            write("sec.json", {"fields": ["cik", "name", "ticker", "exchange"],
                               "data": [[12345, "Repair Corp", "FIX", "NYSE"]]})
            write("CIK0000012345.json", {"cik": 12345, "facts": {
                "us-gaap": {
                    "StockholdersEquity": {"units": {"USD": [fact(1500, "2026-09-30")]}},
                    "NetIncomeLoss": {"units": {"USD": [fact(90, "2026-09-30", start="2025-10-01")]}},
                },
                "dei": {"EntityCommonStockSharesOutstanding": {
                    "units": {"shares": [fact(100, "2026-10-13")]}
                }},
            }})
            output = self.replay(audit, root)
            self.assertEqual(output, self.replay(audit, root))
            report = json.loads(output)
            self.assertEqual(report["increase"], {"closes": 1, "screened": 1, "alert_candidates": 1})
            self.assertEqual(report["eligible_for_replay"], 1)
            self.assertEqual(report["additional_alert_candidates"], ["FIX"])
            self.assertEqual(report["repeated_alert_candidates"], 0)
            self.assertEqual(report["held"], {"CHANGE": "exact_dated_listing_pair_unavailable"})


if __name__ == "__main__":
    unittest.main()
