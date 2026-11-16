import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export-jquants-personal-quotes.py"
spec = importlib.util.spec_from_file_location("jquants_personal_quotes", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class JQuantsExportTest(unittest.TestCase):
    def test_provenance_matches_saved_snapshot_and_excludes_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "quotes.csv"
            receipt = io.StringIO()
            args = [str(SCRIPT), "--date", "2026-03-31", "--require-all",
                    "--output", str(snapshot), "--provenance", "7203"]
            with patch.dict(exporter.os.environ, {"JQUANTS_API_KEY": "fixture-key"}), \
                    patch.object(exporter.sys, "argv", args), \
                    patch.object(exporter.sys, "stderr", receipt), \
                    patch.object(exporter, "collect_session_quotes", return_value=[
                        ("JP:7203", "2026-03-31", "JPY", 3000)
                    ]):
                exporter.main()
            proof = json.loads(receipt.getvalue())
            self.assertEqual(proof["csv_sha256"], hashlib.sha256(snapshot.read_bytes()).hexdigest())
            self.assertEqual(proof["requested_period"], {"first": "2026-03-31", "last": "2026-03-31"})
            self.assertEqual(proof["requested_codes"], ["7203"])
            self.assertEqual(proof["observations"], 1)
            self.assertEqual(proof["price_basis"], "unadjusted_close")
            self.assertEqual(proof["purpose"], "personal")
            self.assertTrue(proof["retrieved_at_utc"].endswith("+00:00"))
            self.assertNotIn("fixture-key", receipt.getvalue())

    def test_snapshot_preserves_previous_file_until_a_complete_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "current.csv"
            previous = "market_id,date,currency,close\nJP:7203,2026-03-31,JPY,2900\n"
            snapshot.write_text(previous, encoding="utf-8")
            args = [str(SCRIPT), "--date", "2026-03-31", "--require-all",
                    "--output", str(snapshot), "7203", "7201"]
            toyota = ("JP:7203", "2026-03-31", "JPY", 3000)
            nissan = ("JP:7201", "2026-03-31", "JPY", 350)
            with patch.dict(exporter.os.environ, {"JQUANTS_API_KEY": "example"}), \
                    patch.object(exporter.sys, "argv", args), \
                    patch.object(exporter.sys, "stderr", io.StringIO()), \
                    patch.object(exporter, "collect_session_quotes") as collect:
                for failure, partial_rows in [(URLError("unavailable"), None), (None, [toyota])]:
                    collect.side_effect = failure
                    collect.return_value = partial_rows
                    with self.assertRaises(SystemExit) as error:
                        exporter.main()
                    self.assertEqual(error.exception.code, 1)
                    self.assertEqual(snapshot.read_text(encoding="utf-8"), previous)
                collect.side_effect = None
                collect.return_value = [toyota, nissan]
                exporter.main()
            self.assertEqual(snapshot.read_text(encoding="utf-8"),
                             "market_id,date,currency,close\nJP:7203,2026-03-31,JPY,3000\n"
                             "JP:7201,2026-03-31,JPY,350\n")
            self.assertEqual(list(Path(directory).iterdir()), [snapshot])

    def test_snapshot_write_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "current.csv"
            snapshot.write_text("previous snapshot", encoding="utf-8")
            with patch.object(exporter, "write_quotes", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    exporter.save_snapshot(snapshot, [])
            self.assertEqual(snapshot.read_text(encoding="utf-8"), "previous snapshot")
            self.assertEqual(list(Path(directory).iterdir()), [snapshot])

    def test_uses_unadjusted_close_and_paginates(self):
        pages = iter([
            {"data": [{"Code": "72030", "Date": "2026-03-30", "C": None}], "pagination_key": "next"},
            {"data": [{"Code": "72030", "Date": "2026-03-31", "C": 3100.5, "AdjC": 900}]},
        ])
        queries = []

        def fetch(query, _key):
            queries.append(dict(query))
            return next(pages)

        result = exporter.collect_quotes("7203", "2026-03-30", "2026-03-31", "example", fetch)
        self.assertEqual(result, [("JP:7203", "2026-03-31", "JPY", 3100.5)])
        self.assertEqual(queries[0], {"code": "7203", "from": "2026-03-30", "to": "2026-03-31"})
        self.assertEqual(queries[1], {**queries[0], "pagination_key": "next"})

    def test_rejects_mismatched_code_or_date_and_repeated_pages(self):
        invalid_pages = [
            {"data": [{"Code": "72031", "Date": "2026-03-31", "C": 3000}]},
            {"data": [{"Code": "72030", "Date": "2026-04-01", "C": 3000}]},
            {"data": [], "pagination_key": "repeated"},
        ]
        for page in invalid_pages:
            with self.subTest(page=page), self.assertRaises(ValueError):
                exporter.collect_quotes("7203", "2026-03-30", "2026-03-31", "example", lambda *_: page)

    def test_session_selects_exact_date_and_common_stock_codes(self):
        day = "2026-03-31"
        pages = iter([
            {"data": [
                {"Code": "72031", "Date": day, "C": 50},
                {"Code": "72030", "Date": day, "C": 3100.5, "AdjC": 900},
                {"Code": "38610", "Date": day, "C": None},
            ], "pagination_key": "next"},
            {"data": [{"Code": "130A0", "Date": day, "C": 600}]},
        ])
        queries = []

        def fetch(query, _key):
            queries.append(dict(query))
            return next(pages)

        self.assertEqual(
            exporter.collect_session_quotes(["7203", "3861", "130A"], day, "example", fetch),
            [("JP:130A", day, "JPY", 600), ("JP:7203", day, "JPY", 3100.5)],
        )
        self.assertEqual(queries, [{"date": day}, {"date": day, "pagination_key": "next"}])

    def test_session_rejects_wrong_date_and_conflicting_close(self):
        day = "2026-03-31"
        for items in [
            [{"Code": "72030", "Date": "2026-03-30", "C": 3000}],
            [{"Code": "72030", "Date": day, "C": price} for price in (3000, 3100)],
        ]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                exporter.collect_session_quotes(["7203"], day, "example", lambda *_: {"data": items})


class ToyotaRefreshPairTest(unittest.TestCase):
    def test_pair_commits_two_validated_snapshots_or_keeps_destination_absent(self):
        from datetime import datetime, timezone
        from subprocess import CompletedProcess
        refresh_script = SCRIPT.with_name("refresh-jquants-personal.py")
        module_spec = importlib.util.spec_from_file_location("jquants_refresh", refresh_script)
        refresh = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(refresh)
        live_capture = refresh.capture
        days = ("2026-06-30", "2026-09-30")
        exported_days = []

        def capture(command, **options):
            if str(command[1]) != str(SCRIPT):
                return live_capture(command, **options)
            self.assertEqual(command[-2:], ["--", "7203"])
            day = command[-4].split("=")[1]
            self.assertEqual(command[-3], f"--to={day}")
            exported_days.append(day)
            csv_digest = exporter.save_snapshot(
                command[command.index("--output") + 1], [("JP:7203", day, "JPY", 3000)])
            receipt = io.StringIO()
            with patch.object(exporter.sys, "stderr", receipt):
                exporter.report_provenance([day], ["7203"], day, day, csv_digest,
                                           datetime(2026, 11, 16, 0, 0, len(exported_days), tzinfo=timezone.utc))
            return CompletedProcess(command, 0, "", receipt.getvalue())

        with tempfile.TemporaryDirectory() as directory, patch.object(refresh, "capture", side_effect=capture):
            root = Path(directory)
            out = root / "pair"
            self.assertEqual(refresh.refresh_toyota_pair(out, days), 0)
            self.assertEqual(exported_days, list(days))
            final = json.loads((out / "later/report.json").read_text(encoding="utf-8"))
            self.assertTrue(final["latestTrialCheck"]["passed"])
            self.assertEqual(final["latestTrialCheck"]["results"][0]["previousDate"], days[0])
            self.assertTrue((out / "earlier/receipt.json").is_file())

            incomplete = root / "incomplete"
            self.assertEqual(refresh.refresh_toyota_pair(incomplete, (days[0], "2026-10-01")), 2)
            self.assertTrue((incomplete / "later/report.json").is_file())

            failed = root / "failed"

            def fail_later(command, **options):
                if str(command[1]) == str(SCRIPT) and f"--from={days[1]}" in command:
                    raise ValueError("provider unavailable")
                return capture(command, **options)

            with patch.object(refresh, "capture", side_effect=fail_later):
                with self.assertRaisesRegex(ValueError, "provider unavailable"):
                    refresh.refresh_toyota_pair(failed, days)
            self.assertFalse(failed.exists())
            self.assertEqual(sorted(item.name for item in root.iterdir()), ["incomplete", "pair"])
