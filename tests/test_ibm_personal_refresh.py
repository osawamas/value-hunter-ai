"""Offline tests for IBM daily-close retrieval and filing reconciliation."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
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
    def test_scheduled_preflight_reuses_one_response_and_retains_latest_dates(self):
        series = {day: {"4. close": "200"} for day in
                  ("2026-06-30", "2026-09-30", "2026-11-12", "2026-11-13")}
        payload = {"Meta Data": {"2. Symbol": "IBM"}, "Time Series (Daily)": series}
        response = (payload, "2026-11-17T00:00:00+00:00")
        with patch.object(refresh, "fetch_daily_series", return_value=response) as provider:
            report = refresh.scheduled_preflight("fixture", demo=True)
            provider.assert_called_once_with("fixture")
        self.assertEqual(report["preflightChecks"]["current"]["date"], "2026-11-13")
        self.assertEqual(report["exactDateCheck"]["status"], "passed")
        self.assertEqual(report["exactDateCheck"]["checks"]["current"]["date"], "2026-09-30")
        latest_match = report["exactDateCheck"]["checks"]["current"]
        self.assertEqual(latest_match["shareDisclosureDate"], "2026-10-22")
        self.assertEqual(latest_match["shareSource"],
                         "https://www.sec.gov/Archives/edgar/data/51143/000005114326000095/ibm-20260930.htm")
        self.assertNotIn("shares", latest_match)
        self.assertNotIn("valuation", latest_match)
        series["2026-06-30"]["4. close"] = "0"
        with patch.object(refresh, "fetch_daily_series", return_value=response):
            report = refresh.scheduled_preflight("fixture", demo=True)
        self.assertEqual(report["exactDateCheck"]["status"], "invalid_close")
        del series["2026-06-30"]
        with patch.object(refresh, "fetch_daily_series", return_value=response):
            report = refresh.scheduled_preflight("fixture", demo=True)
        self.assertEqual(report["exactDateCheck"]["status"], "insufficient_matching_sessions")
        self.assertEqual(report["preflightChecks"]["current"]["date"], "2026-11-13")

    def test_automatic_comparison_matches_provider_dates_to_filings(self):
        payload = {
            "Meta Data": {"2. Symbol": "IBM"},
            "Time Series (Daily)": {
                day: {"4. close": "200"} for day in ("2026-06-30", "2026-09-30", "2026-11-13")
            },
        }
        def fetch(query, dates, *, share_dates):
            return refresh.read_closes(payload, dates, share_dates), "2026-11-17T00:00:00+00:00"

        with patch("sys.argv", ["check-ibm-personal-refresh.py", "--demo", "--latest-with-filings"]), \
                patch.object(refresh, "fetch_closes", side_effect=fetch) as provider, \
                redirect_stdout(StringIO()) as output:
            self.assertEqual(refresh.main(), 0)
        provider.assert_called_once()
        report = json.loads(output.getvalue())
        self.assertEqual([check["date"] for check in report["preflightChecks"].values()],
                         ["2026-06-30", "2026-09-30"])
        self.assertFalse(report["publicRankingEligible"])
        with self.assertRaisesRegex(ValueError, "Fewer than two IBM closes"):
            refresh.read_closes(payload, None, {"2026-09-30"})

    def test_latest_two_uses_provider_trading_dates_and_reports_missing_shares(self):
        payload = {
            "Meta Data": {"2. Symbol": "IBM"},
            "Time Series (Daily)": {
                "2026-11-13": {"4. close": "201"},
                "2026-09-29": {"4. close": "199"},
                "2026-09-30": {"4. close": "200"},
            },
        }
        closes = refresh.read_closes(payload, None)
        self.assertEqual(list(closes), ["2026-09-30", "2026-11-13"])
        with patch("sys.argv", ["check-ibm-personal-refresh.py", "--demo", "--latest-two"]), \
                patch.object(refresh, "fetch_closes", return_value=(closes, "2026-11-16T07:00:00+00:00")) as fetch, \
                redirect_stdout(StringIO()) as output:
            self.assertEqual(refresh.main(), 2)
        fetch.assert_called_once()
        self.assertIsNone(fetch.call_args.args[1])
        report = json.loads(output.getvalue())
        self.assertEqual(report["latestObservedTrials"]["current"]["status"], "no_exact_share_evidence")
        checks = report["preflightChecks"]
        self.assertEqual(checks["previous"]["valuationStatus"], "trial_calculated")
        self.assertEqual(checks["current"], {
            "date": "2026-11-13",
            "closeStatus": "retrieved",
            "valuationStatus": "no_exact_share_evidence",
            "referenceShareDate": "2026-09-30",
            "referenceShareSource": report["latestObservedTrials"]["current"]["referenceShareSource"],
        })
        self.assertFalse(report["publicRankingEligible"])
        del payload["Time Series (Daily)"]["2026-09-29"]
        del payload["Time Series (Daily)"]["2026-09-30"]
        with self.assertRaisesRegex(ValueError, "fewer than two"):
            refresh.read_closes(payload, None)

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
            self.assertEqual(report["preflightChecks"]["current"]["valuationStatus"], "trial_calculated")
            self.assertEqual(fetch.call_count, 2)
            (old / "quotes.csv").write_text("modified")
            with self.assertRaisesRegex(ValueError, "does not match its receipt"):
                refresh.save_refresh(unused, old, "", dates[1], demo=True)
            self.assertFalse(unused.exists())
            self.assertEqual(fetch.call_count, 2)
