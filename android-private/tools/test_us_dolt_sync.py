import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from us_dolt_sync import sync


class SyncTest(unittest.TestCase):
    def test_zero_exit_without_clone_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner), 'invalid_repository_after_command')
            self.assertFalse(dest.exists())

    def test_zero_exit_after_existing_repository_disappears(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner), 'invalid_repository_after_command')

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

    def test_rate_limit_recovery_on_third_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            calls, waits = [], []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1 if len(calls) < 3 else 0,
                                       stderr='HTTP 429' if len(calls) < 3 else '',
                                       stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=waits.append,
                                  attempts=3), 'updated')
            self.assertEqual(waits, [60, 120])
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(cmd == ['dolt', 'pull', '--ff-only'] for cmd in calls))
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_three_rate_limits_exhaust_backoff_without_mutating_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            calls, waits = [], []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='', stdout='Too Many Requests (429)')
            self.assertEqual(sync(dest, runner=runner, sleeper=waits.append,
                                  attempts=3), 'cached_after_rate_limit')
            self.assertEqual(waits, [60, 120])
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(cmd == ['dolt', 'pull', '--ff-only'] for cmd in calls))
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_failed_pull_with_disappeared_cache_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('unexpected retry')), 'invalid_repository_after_command')

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

    def test_timeout_keeps_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                raise subprocess.TimeoutExpired(cmd, 180)
            self.assertEqual(sync(dest, runner=runner), 'cached_after_timeout')
            self.assertEqual(len(calls), 1)
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_timeout_with_disappeared_cache_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                raise subprocess.TimeoutExpired(cmd, 180)
            self.assertEqual(sync(dest, runner=runner), 'invalid_repository_after_command')

    def test_timeout_initial_clone_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                (dest / '.dolt').mkdir(parents=True)
                raise subprocess.TimeoutExpired(cmd, 180)
            self.assertEqual(sync(dest, runner=runner), 'timed_out')
            self.assertEqual(len(calls), 1)

    def test_missing_dolt_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            def runner(cmd, **kwargs):
                raise FileNotFoundError('dolt')
            self.assertEqual(sync(Path(tmp) / 'stocks', runner=runner), 'dolt_not_installed')

    def test_os_error_keeps_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            def runner(cmd, **kwargs):
                raise PermissionError('cannot execute')
            self.assertEqual(sync(dest, runner=runner), 'cached_after_os_error')
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_os_error_with_disappeared_cache_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                raise PermissionError('cannot execute')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')

    def test_os_error_on_first_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            def runner(cmd, **kwargs):
                raise OSError('cannot spawn')
            self.assertEqual(sync(Path(tmp) / 'stocks', runner=runner), 'os_error')

    def test_empty_subprocess_output_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                return SimpleNamespace(returncode=1, stderr=None, stdout=None)
            self.assertEqual(sync(dest, runner=runner), 'failed')

    def test_unrelated_1429_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='error 1429: invalid data', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('unexpected sleep')), 'failed')
            self.assertEqual(len(calls), 1)

    def test_rate_limit_in_stdout_uses_cache_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            calls, waits = [], []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='', stdout='HTTP status=429')
            self.assertEqual(sync(dest, runner=runner, sleeper=waits.append), 'cached_after_rate_limit')
            self.assertEqual(waits, [60])
            self.assertEqual(len(calls), 2)
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_unrelated_4290_does_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='error 4290: invalid data', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('unexpected sleep')), 'failed')
            self.assertEqual(len(calls), 1)

    def test_initial_rate_limit_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                (dest / '.dolt').mkdir(parents=True)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('unexpected sleep')), 'rate_limited')
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
