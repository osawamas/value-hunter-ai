"""Regression guard for the generated JPX rights asset; no network or APK required."""
import json
import unittest
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ASSET = Path(__file__).resolve().parents[1] / "android-private/app/src/main/assets/jpx-share-rights.json"


class JpxRightsAssetIntegrityTest(unittest.TestCase):
    def test_generated_asset_is_well_formed_and_unambiguous(self):
        payload = json.loads(ASSET.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        revision = payload["revision"]
        self.assertIsInstance(revision, str)
        self.assertIsNotNone(datetime.fromisoformat(revision.replace("Z", "+00:00")).tzinfo)
        rows = payload["adjustments"]
        self.assertIsInstance(rows, list)
        self.assertTrue(rows, "Empty rights data must not silently pass")
        seen = {}
        for index, row in enumerate(rows):
            with self.subTest(row=index):
                self.assertIsInstance(row, list)
                self.assertEqual(len(row), 5)
                symbol, ex_date, record_date, numerator, denominator = row
                self.assertRegex(symbol, r"^[0-9][0-9A-Z]{3}$")
                first = date.fromisoformat(ex_date)
                second = date.fromisoformat(record_date)
                self.assertLessEqual(first, second)
                try:
                    n, d = Decimal(numerator), Decimal(denominator)
                except (InvalidOperation, TypeError) as exc:
                    self.fail(f"Non-numeric adjustment ratio: {exc}")
                self.assertTrue(n.is_finite() and d.is_finite())
                self.assertGreater(n, 0)
                self.assertGreater(d, 0)
                key = (symbol, record_date, ex_date)
                self.assertNotIn(key, seen, f"Ambiguous duplicate adjustment: {key}")
                seen[key] = (n, d)


if __name__ == "__main__":
    unittest.main()
