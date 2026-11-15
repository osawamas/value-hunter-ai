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
        joined = {row["id"]: row for row in records if "quarterly" in row}
        self.assertEqual(set(excerpts), set(joined))
        for key, row in joined.items():
            with self.subTest(company=key):
                expected = row["quarterly"]
                report = {**expected, "period_end": expected["periods"][-1]["end"]}
                actual = quarters.build_quarter(json.dumps(excerpts[key]).encode(), row, report)
                self.assertEqual(actual["periods"], expected["periods"])
