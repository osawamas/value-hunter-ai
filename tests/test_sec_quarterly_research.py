from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("build_sec_quarters", ROOT / "scripts/build-sec-quarterly-research.py")
quarters = module_from_spec(SPEC)
SPEC.loader.exec_module(quarters)


class SecQuarterlyResearchTest(unittest.TestCase):
    def test_issuer_quarters_match_filing_facts(self):
        records = json.loads((ROOT / "docs/data/market-research-v315.json").read_text())["records"]
        excerpts = json.loads((ROOT / "tests/fixtures/sec-quarterly-excerpts-v332.json").read_text())
        joined = {row["id"]: row for row in records if row["market"] == "US" and "quarterly" in row}
        self.assertEqual(set(excerpts), set(joined))
        for key, row in joined.items():
            with self.subTest(company=key):
                expected = row["quarterly"]
                report = {**expected, "period_end": expected["periods"][-1]["end"]}
                actual = quarters.build_quarter(json.dumps(excerpts[key]).encode(), row, report)
                self.assertEqual(actual["periods"], expected["periods"])
                self.assertEqual(actual.get("shares"), expected.get("shares"))
                if row["financials"].get("share_classes"):
                    self.assertNotIn("shares", actual)
                    self.assertEqual(excerpts[key]["reviewed_cover"], expected["share_classes"])
                    annual_classes = row["financials"]["share_classes"]["classes"]
                    self.assertEqual(
                        [(item["label"], item["symbol"]) for item in annual_classes],
                        [(item["label"], item["symbol"]) for item in expected["share_classes"]["classes"]],
                    )
