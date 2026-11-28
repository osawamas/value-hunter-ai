from datetime import date
from unittest import TestCase
from unittest.mock import Mock

from us_finzdata_probe import audit


class FinzDataProbeTest(TestCase):
    def test_only_free_plan_can_request_unadjusted_exact_date(self):
        day = date(2026, 11, 27)
        fetch = Mock(side_effect=[b'{"plan":"free"}', b"date,symbol,close\n2026-11-27,AAPL,100.01\n"])
        self.assertEqual(audit(day, "test-key", fetch)["status"], "target_close_available")
        self.assertEqual(fetch.call_args.args[2]["adjust"], "none")
        fetch = Mock(return_value=b'{"plan":"paid"}')
        self.assertEqual(audit(day, "test-key", fetch)["status"], "free_plan_unverified")
        fetch.assert_called_once()
        fetch.reset_mock()
        self.assertEqual(audit(day, "", fetch)["status"], "key_unconfigured")
        fetch.assert_not_called()

    def test_rejects_a_different_session(self):
        fetch = Mock(side_effect=[b'{"plan":"free"}', b"date,symbol,close\n2026-11-26,AAPL,100.01\n"])
        self.assertEqual(audit(date(2026, 11, 27), "test-key", fetch)["status"], "response_unverified")
