from datetime import date
import unittest

from us_alpaca_close_probe import audit


class AlpacaCloseProbeTest(unittest.TestCase):
    def test_checks_both_symbols_and_rejects_another_session(self):
        def fetch(*_):
            bar = {"t": "2026-11-27T05:00:00Z", "c": 100}
            return {"bars": {"AAPL": [bar], "IBM": [bar]}}

        self.assertEqual(audit(date(2026, 11, 27), "key", "secret", fetch)["verified"], 2)
        self.assertEqual(audit(date(2026, 11, 26), "key", "secret", fetch)["status"], "response_unverified")

    def test_skips_without_both_keys(self):
        self.assertEqual(audit(date(2026, 11, 27), "key", "")["status"], "key_unconfigured")
