import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export-jquants-personal-quotes.py"
spec = importlib.util.spec_from_file_location("jquants_personal_quotes", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class JQuantsExportTest(unittest.TestCase):
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
