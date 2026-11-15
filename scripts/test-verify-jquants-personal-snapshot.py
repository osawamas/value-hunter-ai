#!/usr/bin/env python3
"""Regression tests for the offline personal J-Quants receipt verifier."""
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location('verify_snapshot', Path(__file__).with_name('verify-jquants-personal-snapshot.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
refresh_spec = importlib.util.spec_from_file_location(
    "refresh_snapshot", Path(__file__).with_name("refresh-jquants-personal.py")
)
refresher = importlib.util.module_from_spec(refresh_spec)
refresh_spec.loader.exec_module(refresher)

class SnapshotTests(unittest.TestCase):
    def test_refresh_saves_a_validated_pair_and_preserves_it_on_failure(self):
        baseline = self.csv.with_name("baseline")
        current = self.csv.with_name("current")
        original_capture = refresher.capture
        timestamp = "2026-10-01T00:00:00.000001Z"
        close = "2500"

        def capture(command):
            if Path(command[1]).name != "export-jquants-personal-quotes.py":
                return original_capture(command)
            output = command[command.index("--output") + 1]
            raw = f"market_id,date,currency,close\nJP:7203,2026-09-30,JPY,{close}\n".encode()
            output.write_bytes(raw)
            receipt = {**self.record, "retrieved_at_utc": timestamp,
                       "csv_sha256": hashlib.sha256(raw).hexdigest()}
            return subprocess.CompletedProcess(command, 0, "", json.dumps(receipt))

        with patch.object(refresher, "capture", side_effect=capture):
            refresher.refresh(baseline, None, [])
            first = json.loads((baseline / "report.json").read_text())
            self.assertEqual(first["snapshotVerification"], "jquants_personal_receipt_matched")
            self.assertEqual(first["snapshots"]["current"]["observations"], 1)
            toyota = first["results"][0]
            self.assertEqual(toyota["status"], "trial_calculated")
            self.assertEqual(toyota["valuation"]["cap"], 2500 * 11778247313)
            self.assertGreater(toyota["valuation"]["per"], 0)
            self.assertGreater(toyota["valuation"]["pbr"], 0)
            original = (baseline / "quotes.csv").read_bytes()
            with self.assertRaisesRegex(ValueError, "increasing order"):
                refresher.refresh(current, baseline, [])
            self.assertFalse(current.exists())
            self.assertEqual((baseline / "quotes.csv").read_bytes(), original)

            timestamp = "2026-10-01T00:00:00.000002Z"
            close = "2501"
            refresher.refresh(current, baseline, [])
            result = json.loads((current / "report.json").read_text())["results"][0]
            self.assertEqual(result["closeChange"], "revised")
            self.assertEqual(result["valuation"]["cap"], 2501 * 11778247313)
            self.assertEqual({p.name for p in current.iterdir()}, {"quotes.csv", "receipt.json", "report.json"})
            with self.assertRaisesRegex(ValueError, "already exists"):
                refresher.refresh(current, baseline, [])
            self.assertFalse(list(current.parent.glob(".jquants-*")))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.csv = Path(self.temp.name) / 'quotes.csv'
        self.receipt = Path(self.temp.name) / 'receipt.json'
        self.csv.write_text('market_id,date,currency,close\nJP:7203,2026-09-30,JPY,2500\n', encoding='utf-8')
        self.record = {'provider':'J-Quants','purpose':'personal','price_basis':'unadjusted_close',
                       'requested_period':{'first':'2026-09-30','last':'2026-09-30'},
                       'requested_codes':['7203'],'observations':1,
                       'retrieved_at_utc':'2026-10-01T00:00:00.000001+00:00'}
        self.save()
    def save(self):
        self.record['csv_sha256'] = hashlib.sha256(self.csv.read_bytes()).hexdigest()
        self.receipt.write_text(json.dumps(self.record), encoding='utf-8')
    def test_valid(self):
        self.assertEqual(module.validate(self.csv,self.receipt)['observations'],1)

    def test_single_snapshot_rejects_mismatch_and_reports_missing_exact_close(self):
        cli = Path(__file__).with_name("check-representative-valuations.js")
        args = ["node", cli, "--jquants", self.csv, self.receipt]
        self.csv.write_bytes(self.csv.read_bytes().replace(b"2026-09-30", b"2026-10-01"))
        rejected = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 1)
        self.assertEqual(rejected.stdout, "")
        self.assertIn("SHA-256", rejected.stderr)
        self.record["requested_period"] = {"first": "2026-10-01", "last": "2026-10-01"}
        self.save()
        passed = subprocess.run(args, check=True, capture_output=True, text=True)
        toyota = json.loads(passed.stdout)["results"][0]
        self.assertEqual(toyota["status"], "missing_exact_close")
        self.assertNotIn("valuation", toyota)

    def test_tampering(self):
        self.csv.write_text(self.csv.read_text().replace('2500','2501'))
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            module.validate(self.csv,self.receipt)
    def test_duplicate_even_with_matching_hash(self):
        self.csv.write_text(self.csv.read_text()+'JP:7203,2026-09-30,JPY,2500\n')
        self.record['observations']=2
        self.save()
        with self.assertRaisesRegex(ValueError,'duplicate'):
            module.validate(self.csv,self.receipt)
    def test_missing_code(self):
        self.record['requested_codes']=['7203','6758']
        self.save()
        with self.assertRaisesRegex(ValueError,'missing requested'):
            module.validate(self.csv,self.receipt)
    def test_wrong_currency(self):
        self.csv.write_text(self.csv.read_text().replace('JPY','USD'))
        self.save()
        with self.assertRaisesRegex(ValueError,'currency'):
            module.validate(self.csv,self.receipt)
    def test_out_of_range(self):
        self.csv.write_text(self.csv.read_text().replace('2026-09-30','2026-10-01'))
        self.save()
        with self.assertRaisesRegex(ValueError,'outside'):
            module.validate(self.csv,self.receipt)

    def test_comparison_checks_both_receipts_before_calculating(self):
        current = self.csv.with_name("current.csv")
        current_receipt = self.receipt.with_name("current.json")
        current.write_bytes(self.csv.read_bytes().replace(b"2500", b"2501"))
        current_record = {
            **self.record, "csv_sha256": hashlib.sha256(current.read_bytes()).hexdigest(),
            "retrieved_at_utc": "2026-10-01T00:00:00.000002Z",
        }
        current_receipt.write_text(json.dumps(current_record), encoding="utf-8")
        cli = Path(__file__).with_name("check-representative-valuations.js")
        args = ["node", cli, "--compare-jquants", self.csv, self.receipt, current, current_receipt]
        passed = subprocess.run(args, check=True, capture_output=True, text=True)
        report = json.loads(passed.stdout)
        self.assertEqual(report["snapshotVerification"], "jquants_personal_receipts_matched")
        self.assertEqual(report["snapshots"]["current"]["retrievedAtUtc"], "2026-10-01T00:00:00.000002+00:00")
        toyota = report["results"][0]
        self.assertEqual(toyota["closeChange"], "revised")
        self.assertEqual(toyota["valuation"]["cap"], 2501 * 11778247313)
        self.assertGreater(toyota["valuation"]["per"], 0)
        self.assertGreater(toyota["valuation"]["pbr"], 0)
        for candidate in (self.csv, current):
            with self.subTest(candidate=candidate.name):
                original = candidate.read_bytes()
                candidate.write_bytes(original.replace(b"250", b"251"))
                rejected = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(rejected.returncode, 1)
                self.assertEqual(rejected.stdout, "")
                self.assertIn("SHA-256", rejected.stderr)
                candidate.write_bytes(original)
        for timestamp in ("2026-10-01T00:00:00.000001Z", "2026-09-30T23:00:00Z", None, ""):
            with self.subTest(timestamp=timestamp):
                receipt = {**current_record, "retrieved_at_utc": timestamp}
                if timestamp is None:
                    del receipt["retrieved_at_utc"]
                current_receipt.write_text(json.dumps(receipt), encoding="utf-8")
                rejected = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(rejected.returncode, 1)
                self.assertEqual(rejected.stdout, "")
                self.assertIn("retrieval timestamp", rejected.stderr)
        current.write_bytes(current.read_bytes().replace(b"7203", b"7201"))
        current_receipt.write_text(json.dumps({
            **current_record, "requested_codes": ["7201"],
            "csv_sha256": hashlib.sha256(current.read_bytes()).hexdigest(),
        }), encoding="utf-8")
        rejected = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 1)
        self.assertEqual(rejected.stdout, "")
        self.assertIn("same requested securities", rejected.stderr)

if __name__=='__main__':
    unittest.main()
