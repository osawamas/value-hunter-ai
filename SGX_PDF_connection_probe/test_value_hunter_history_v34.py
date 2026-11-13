import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from value_hunter_history_v34 import build_index, save, snapshot


def sample(day="2026-11-13"):
    return {"schema_version": "value_hunter_web_v29", "ranking_enabled": False,
            "ranking_eligible_count": 0, "updated_at_utc": day + "T11:30:00+00:00",
            "records": [{"symbol": "G13", "ranking_eligible": False, "price_sgd": 0.575,
                         "per_reference": 17.77, "pbr_reference_unverified": None,
                         "market_cap_sgd": 6900000000, "quote_freshness": "RECENT",
                         "quote_timestamp_utc": day + "T09:00:00+00:00",
                         "shares_as_of_date": "2026-08-14", "quality_flags": []}]}


class V34Tests(unittest.TestCase):
    def test_snapshot(self):
        result = snapshot(sample())
        self.assertEqual(result["date_utc"], "2026-11-13")
        self.assertEqual(result["quote_count"], 1)
        self.assertEqual(result["records"][0]["price_sgd"], 0.575)

    def test_two_days_sorted(self):
        a = snapshot(sample("2026-11-12"))
        b = snapshot(sample("2026-11-13"))
        index = build_index(build_index(None, a), b)
        self.assertEqual(index["retained_days"], 2)
        self.assertEqual(index["entries"][0]["date_utc"], "2026-11-12")

    def test_same_day_replace(self):
        a = snapshot(sample())
        b = deepcopy(a)
        b["records"][0]["price_sgd"] = 0.6
        index = build_index(build_index(None, a), b)
        self.assertEqual(index["retained_days"], 1)
        self.assertEqual(index["entries"][0]["records"][0]["price_sgd"], 0.6)

    def test_90_days_limit(self):
        index = None
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for n in range(100):
            date = (base + timedelta(days=n)).date().isoformat()
            index = build_index(index, snapshot(sample(date)))
        self.assertEqual(index["retained_days"], 90)

    def test_save_files(self):
        with tempfile.TemporaryDirectory() as folder:
            index = save(sample(), folder)
            self.assertEqual(index["retained_days"], 1)
            self.assertTrue(Path(folder, "index.json").exists())
            self.assertTrue(Path(folder, "2026-11-13.json").exists())

    def test_missing_quote_not_made_up(self):
        feed = sample()
        feed["records"][0]["price_sgd"] = None
        result = snapshot(feed)
        self.assertIsNone(result["records"][0]["price_sgd"])
        self.assertEqual(result["quote_count"], 0)

    def test_unknown_schema_rejected(self):
        feed = sample()
        feed["schema_version"] = "future"
        with self.assertRaises(ValueError):
            snapshot(feed)

    def test_ranking_not_promoted(self):
        feed = sample()
        feed["ranking_eligible_count"] = 1
        with self.assertRaises(ValueError):
            snapshot(feed)

    def test_duplicate_symbol_blocked(self):
        feed = sample()
        feed["records"].append(deepcopy(feed["records"][0]))
        with self.assertRaises(ValueError):
            snapshot(feed)


if __name__ == "__main__":
    unittest.main()
