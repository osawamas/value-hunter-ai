"""Offline tests for IBM daily-close retrieval and filing reconciliation."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

spec = spec_from_file_location(
    "ibm_refresh", Path(__file__).resolve().parents[1] / "scripts/check-ibm-personal-refresh.py"
)
refresh = module_from_spec(spec)
spec.loader.exec_module(refresh)


class IBMRefreshTests(unittest.TestCase):
    def test_daily_closes_with_and_without_share_evidence(self):
        days = ("2026-09-30", "2026-11-13")
        payload = {
            "Meta Data": {"2. Symbol": "IBM"},
            "Time Series (Daily)": {day: {"4. close": str(200 + i)} for i, day in enumerate(days)},
        }
        closes = refresh.read_closes(payload, days)
        report = refresh.compare(closes, *days, demo=True)
        self.assertFalse(report["passed"])
        self.assertFalse(report["publicRankingEligible"])
        self.assertEqual(report["retrievals"], 1)
        previous, current = (report["latestObservedTrials"][key] for key in ("previous", "current"))
        self.assertEqual(previous["valuation"]["cap"], 200 * 945120805)
        self.assertEqual(current["status"], "no_exact_share_evidence")
        self.assertEqual(current["referenceShareDate"], days[0])
        self.assertNotIn("valuation", current)
        with self.assertRaisesRegex(ValueError, "No IBM close"):
            refresh.read_closes(payload, ("2026-11-14",))
        payload["Meta Data"]["2. Symbol"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "IBM daily series"):
            refresh.read_closes(payload, days)
