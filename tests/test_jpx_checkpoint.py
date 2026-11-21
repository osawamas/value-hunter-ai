import json
import tempfile
import unittest
from pathlib import Path
from scripts.jpx_checkpoint import merge_checkpoint, save_atomic

U = ["1234", "5678", "9012"]
def record(ticker, revision=0, **extra):
    return {"ticker": ticker, "revision": revision, **extra}

class CheckpointTests(unittest.TestCase):
    def test_resume_idempotent(self):
        old = {"universe": U, "records": [record("1234")]}
        step = {"universe": U, "records": [record("5678")]}
        merged = merge_checkpoint(old, step)
        self.assertEqual(merged["next_ticker"], "9012")
        self.assertEqual(merge_checkpoint(merged, step), merged)

    def test_correction_requires_revision_and_evidence(self):
        old = {"universe": U, "records": [record("1234", 1)]}
        with self.assertRaises(ValueError):
            merge_checkpoint(old, {"universe": U, "records": [record("1234", 2)]})
        revised = record("1234", 2, source_url="https://example.org/b", source_sha256="b"*64)
        self.assertEqual(merge_checkpoint(old, {"universe": U, "records": [revised]})["records"], [revised])

    def test_stale_or_conflicting_replay(self):
        old = {"universe": U, "records": [record("1234", 2)]}
        for rev in (1, 2):
            with self.assertRaises(ValueError):
                merge_checkpoint(old, {"universe": U, "records": [record("1234", rev, on_hold=True)]})

    def test_duplicate_and_universe_order(self):
        old = {"universe": U, "records": []}
        with self.assertRaises(ValueError):
            merge_checkpoint(old, {"universe": U[::-1], "records": []})
        with self.assertRaises(ValueError):
            merge_checkpoint(old, {"universe": U, "records": [record("1234"), record("1234")]})

    def test_atomic_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            save_atomic(path, {"next_ticker": "5678"})
            self.assertEqual(json.loads(path.read_text())["next_ticker"], "5678")
            self.assertEqual(list(Path(directory).iterdir()), [path])
