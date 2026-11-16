import json
import tempfile
import unittest
from pathlib import Path

from sgx_s63_buyback_v109 import URL
from test_sgx_s63_buyback_v109 import sample
from update_android_s63_shares import update_ledger


class AndroidS63LedgerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "shares.json"
        self.path.write_text('{"schema":1,"symbol":"S63","records":[]}', encoding="utf-8")

    def test_ingests_verified_notice_once(self):
        self.assertEqual(update_ledger(self.path, [URL, URL], lambda _: sample()), ["2026-11-13"])
        row, = json.loads(self.path.read_text())["records"]
        self.assertEqual(row["shares"], 3_115_847_115)
        self.assertEqual(row["disclosed_at"], "2026-11-13T18:21:18+08:00")
        self.assertEqual(row["source"], URL)
        unchanged = self.path.read_bytes()
        self.assertEqual(update_ledger(self.path, [URL], lambda _: sample()), [])
        self.assertEqual(self.path.read_bytes(), unchanged)

    def test_short_url_is_idempotent_with_the_long_url(self):
        short_url = URL.rsplit("/", 1)[0] + "/"
        self.assertEqual(update_ledger(self.path, [short_url], lambda _: sample()), ["2026-11-13"])
        baseline = self.path.read_bytes()
        self.assertEqual(update_ledger(self.path, [URL], lambda _: sample()), [])
        self.assertEqual(self.path.read_bytes(), baseline)
        other = short_url.replace("4NRLOX68RVAQLTX7", "DIFFERENT")
        with self.assertRaisesRegex(ValueError, "Conflicting S63"):
            update_ledger(self.path, [other], lambda _: sample())

    def test_delayed_notice_keeps_purchase_date_and_broadcast_separate(self):
        delayed = (sample().replace(b"13-Nov-2026", b"14-Nov-2026")
                   .replace(b"SG261113OTHR", b"SG261114OTHR"))
        self.assertEqual(update_ledger(self.path, [URL], lambda _: delayed), ["2026-11-13"])
        row, = json.loads(self.path.read_text(encoding="utf-8"))["records"]
        self.assertEqual(row["date"], "2026-11-13")
        self.assertEqual(row["disclosed_at"], "2026-11-14T18:21:18+08:00")

    def test_rejects_future_broadcast_even_for_an_existing_purchase_date(self):
        future = (sample().replace(b"13-Nov-2026", b"13-Nov-2099")
                  .replace(b"SG261113OTHR", b"SG991113OTHR"))
        baseline = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Invalid date"):
            update_ledger(self.path, [URL], lambda _: future)
        self.assertEqual(self.path.read_bytes(), baseline)

    def test_rejects_conflict_and_rolls_back_invalid_batch(self):
        baseline = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "official SGXNet"):
            update_ledger(self.path, [URL, "https://example.com/notice"], lambda _: sample())
        self.assertEqual(self.path.read_bytes(), baseline)
        update_ledger(self.path, [URL], lambda _: sample())
        baseline = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Conflicting S63"):
            update_ledger(self.path, [URL], lambda _: sample().replace(b"3,115,847,115", b"3,115,800,000"))
        self.assertEqual(self.path.read_bytes(), baseline)


if __name__ == "__main__":
    unittest.main()
