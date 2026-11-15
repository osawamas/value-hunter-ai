#!/usr/bin/env python3
"""Regression tests for the offline personal J-Quants receipt verifier."""
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('verify_snapshot', Path(__file__).with_name('verify-jquants-personal-snapshot.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.csv = Path(self.temp.name) / 'quotes.csv'
        self.receipt = Path(self.temp.name) / 'receipt.json'
        self.csv.write_text('market_id,date,currency,close\nJP:7203,2026-09-30,JPY,2500\n', encoding='utf-8')
        self.record = {'provider':'J-Quants','purpose':'personal','price_basis':'unadjusted_close',
                       'requested_period':{'first':'2026-09-30','last':'2026-09-30'},
                       'requested_codes':['7203'],'observations':1}
        self.save()
    def save(self):
        self.record['csv_sha256'] = hashlib.sha256(self.csv.read_bytes()).hexdigest()
        self.receipt.write_text(json.dumps(self.record), encoding='utf-8')
    def test_valid(self):
        self.assertEqual(module.validate(self.csv,self.receipt)['observations'],1)
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
        current_receipt.write_text(json.dumps({
            **self.record, "csv_sha256": hashlib.sha256(current.read_bytes()).hexdigest()
        }), encoding="utf-8")
        cli = Path(__file__).with_name("check-representative-valuations.js")
        args = ["node", cli, "--compare-jquants", self.csv, self.receipt, current, current_receipt]
        passed = subprocess.run(args, check=True, capture_output=True, text=True)
        report = json.loads(passed.stdout)
        self.assertEqual(report["snapshotVerification"], "jquants_personal_receipts_matched")
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

if __name__=='__main__':
    unittest.main()
