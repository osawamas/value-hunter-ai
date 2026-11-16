"""Offline tests for IBM daily-close retrieval and filing reconciliation."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

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

    def test_two_historical_sessions_match_same_date_filings(self):
        earlier, later = "2026-06-30", "2026-09-30"
        report = refresh.compare({earlier: 200, later: 201}, earlier, later, demo=True,
                                 retrieved_at=("2026-11-16T04:00:00+00:00", "2026-11-16T04:00:01+00:00"))
        self.assertTrue(report["passed"])
        self.assertFalse(report["publicRankingEligible"])
        self.assertEqual(report["retrievals"], 2)
        previous, current = (report["latestObservedTrials"][key] for key in ("previous", "current"))
        self.assertEqual(previous["shares"], 942134390)
        self.assertEqual(previous["shareDisclosureDate"], "2026-07-23")
        self.assertEqual(current["shares"], 945120805)

    def test_saved_refresh_uses_validated_previous_snapshot(self):
        dates = ("2026-06-30", "2026-09-30")
        with TemporaryDirectory() as directory, patch.object(refresh, "fetch_closes") as fetch:
            fetch.side_effect = [
                ({dates[0]: 200}, "2026-11-16T04:00:00+00:00"),
                ({dates[1]: 210}, "2026-11-16T04:00:01+00:00"),
            ]
            old, current, unused = (Path(directory) / name for name in ("old", "current", "unused"))
            self.assertEqual(refresh.save_refresh(old, None, "", dates[0], demo=True), 0)
            self.assertEqual(refresh.save_refresh(current, old, "", dates[1], demo=True), 0)
            report = json.loads((current / "report.json").read_text())
            self.assertTrue(report["passed"])
            self.assertEqual(report["latestObservedTrials"]["previous"]["shares"], 942134390)
            self.assertEqual(report["latestObservedTrials"]["current"]["shares"], 945120805)
            self.assertEqual(fetch.call_count, 2)
            (old / "quotes.csv").write_text("modified")
            with self.assertRaisesRegex(ValueError, "does not match its receipt"):
                refresh.save_refresh(unused, old, "", dates[1], demo=True)
            self.assertFalse(unused.exists())
            self.assertEqual(fetch.call_count, 2)
