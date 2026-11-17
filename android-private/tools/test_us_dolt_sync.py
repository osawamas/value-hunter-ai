import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from us_dolt_sync import sync


class SyncTest(unittest.TestCase):
    def test_clone_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[:3], ['dolt', 'clone', '--depth'])
                (dest / '.dolt').mkdir(parents=True)
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner), 'cloned')

    def test_existing_clone_survives_429(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('original')
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: None), 'cached_after_rate_limit')
            self.assertEqual(len(calls), 2)
            self.assertEqual((dest / 'marker').read_text(), 'original')
            self.assertTrue(all(c == ['dolt', 'pull', '--ff-only'] for c in calls))

    def test_unexpected_error_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='permission denied', stdout='')
            self.assertEqual(sync(dest, runner=runner), 'failed')
            self.assertEqual(len(calls), 1)

    def test_nonrepo_directory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                sync(Path(tmp))


if __name__ == '__main__':
    unittest.main()
