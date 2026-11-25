import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from us_dolt_sync import sync


class SyncTest(unittest.TestCase):

    def test_invalid_attempt_count_rejected_without_running_dolt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                self.fail('invalid attempt count must not execute Dolt')
            for attempts in (0, -1, 4):
                with self.subTest(attempts=attempts):
                    with self.assertRaisesRegex(ValueError, 'attempts must be 1..3'):
                        sync(dest, runner=runner, attempts=attempts)
            self.assertFalse(dest.exists())

    def test_missing_parent_rejected_without_running_dolt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'missing-parent' / 'stocks'
            def runner(cmd, **kwargs):
                self.fail('missing destination parent must not execute Dolt')
            with self.assertRaisesRegex(ValueError, 'destination parent does not exist'):
                sync(dest, runner=runner)
            self.assertFalse(dest.parent.exists())

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

    def test_initial_clone_symlinked_metadata_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            external = root / 'external-metadata'
            external.mkdir()
            def runner(cmd, **kwargs):
                dest.mkdir()
                (dest / '.dolt').symlink_to(external, target_is_directory=True)
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')
            self.assertTrue(external.is_dir())
            self.assertTrue((dest / '.dolt').is_symlink())

    def test_initial_clone_root_symlink_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            other = root / 'unrelated'
            (other / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[:3], ['dolt', 'clone', '--depth'])
                dest.symlink_to(other, target_is_directory=True)
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')
            self.assertTrue(dest.is_symlink())
            self.assertTrue((other / '.dolt').is_dir())

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
            self.assertEqual(sync(dest, runner=runner), 'partial_clone_requires_manual_cleanup')
            self.assertTrue((dest / '.dolt').is_dir())
            self.assertEqual(len(calls), 1)

    def test_timeout_initial_clone_partial_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                dest.mkdir()
                (dest / 'partial').write_text('safe')
                raise subprocess.TimeoutExpired(cmd, 180)
            self.assertEqual(sync(dest, runner=runner),
                             'partial_clone_requires_manual_cleanup')
            self.assertEqual((dest / 'partial').read_text(), 'safe')

    def test_os_error_initial_clone_partial_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                dest.mkdir()
                (dest / 'partial').write_text('safe')
                raise PermissionError('spawn failed')
            self.assertEqual(sync(dest, runner=runner),
                             'partial_clone_requires_manual_cleanup')
            self.assertEqual((dest / 'partial').read_text(), 'safe')

    def test_missing_dolt_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            def runner(cmd, **kwargs):
                raise FileNotFoundError('dolt')
            self.assertEqual(sync(Path(tmp) / 'stocks', runner=runner), 'dolt_not_installed')

    def test_missing_executable_after_cache_removed_is_not_misclassified(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                raise FileNotFoundError('dolt')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')

    def test_missing_executable_during_partial_clone_preserves_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                dest.mkdir()
                (dest / 'partial').write_text('preserve')
                raise FileNotFoundError('dolt')
            self.assertEqual(sync(dest, runner=runner),
                             'partial_clone_requires_manual_cleanup')
            self.assertEqual((dest / 'partial').read_text(), 'preserve')

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

    def test_single_attempt_rate_limit_keeps_cache_without_sleep(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('safe')
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, attempts=1,
                                  sleeper=lambda _: self.fail('unexpected sleep')),
                             'cached_after_rate_limit')
            self.assertEqual(calls, [['dolt', 'pull', '--ff-only']])
            self.assertEqual((dest / 'marker').read_text(), 'safe')

    def test_alphanumeric_429_identifiers_do_not_trigger_backoff(self):
        for message in ('error 429A: invalid identifier', 'error X429: invalid identifier'):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / 'stocks'
                (dest / '.dolt').mkdir(parents=True)
                calls = []
                def runner(cmd, **kwargs):
                    calls.append(cmd)
                    return SimpleNamespace(returncode=1, stderr=message, stdout='')
                self.assertEqual(sync(dest, runner=runner,
                                      sleeper=lambda _: self.fail('unexpected sleep')), 'failed')
                self.assertEqual(len(calls), 1)

    def test_failed_initial_clone_with_partial_directory_requires_manual_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                dest.mkdir()
                (dest / 'partial').write_text('preserve')
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner,
                                  sleeper=lambda _: self.fail('unexpected sleep')),
                             'partial_clone_requires_manual_cleanup')
            self.assertEqual(len(calls), 1)
            self.assertEqual((dest / 'partial').read_text(), 'preserve')

    def test_failed_initial_clone_without_partial_directory_is_rate_limited(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            def runner(cmd, **kwargs):
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner,
                                  sleeper=lambda _: self.fail('unexpected sleep')),
                             'rate_limited')
            self.assertFalse(dest.exists())

    def test_initial_rate_limit_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                (dest / '.dolt').mkdir(parents=True)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('unexpected sleep')), 'partial_clone_requires_manual_cleanup')
            self.assertEqual(len(calls), 1)


    def test_cache_root_removed_during_backoff_stops_before_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                if len(calls) > 1:
                    (dest / '.dolt').mkdir(parents=True)
                    return SimpleNamespace(returncode=0, stderr='', stdout='')
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            def sleeper(seconds):
                self.assertEqual(seconds, 60)
                (dest / '.dolt').rmdir()
                dest.rmdir()
            self.assertEqual(sync(dest, runner=runner, sleeper=sleeper),
                             'invalid_repository_after_command')
            self.assertEqual(calls, [['dolt', 'pull', '--ff-only']])
            self.assertFalse(dest.exists())

    def test_cache_metadata_removed_during_backoff_stops_before_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            (dest / 'marker').write_text('preserve')
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            def sleeper(seconds):
                self.assertEqual(seconds, 60)
                (dest / '.dolt').rmdir()
            self.assertEqual(sync(dest, runner=runner, sleeper=sleeper),
                             'invalid_repository_after_command')
            self.assertEqual(calls, [['dolt', 'pull', '--ff-only']])
            self.assertEqual((dest / 'marker').read_text(), 'preserve')

    def test_symlinked_dolt_metadata_rejected_without_running_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / 'real-metadata'
            real.mkdir()
            dest = root / 'stocks'
            dest.mkdir()
            (dest / '.dolt').symlink_to(real, target_is_directory=True)
            def runner(cmd, **kwargs):
                self.fail('symlinked metadata must never execute Dolt')
            with self.assertRaisesRegex(ValueError, 'not a Dolt repository'):
                sync(dest, runner=runner)
            self.assertTrue(real.is_dir())

    def test_metadata_replaced_with_symlink_during_backoff_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            real = root / 'other-metadata'
            real.mkdir()
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            def sleeper(seconds):
                self.assertEqual(seconds, 60)
                (dest / '.dolt').rmdir()
                (dest / '.dolt').symlink_to(real, target_is_directory=True)
            self.assertEqual(sync(dest, runner=runner, sleeper=sleeper),
                             'invalid_repository_after_command')
            self.assertEqual(len(calls), 1)
            self.assertTrue(real.is_dir())


    def test_destination_swapped_to_symlink_during_backoff_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            other = root / 'other'
            (other / '.dolt').mkdir(parents=True)
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            def sleeper(seconds):
                self.assertEqual(seconds, 60)
                (dest / '.dolt').rmdir()
                dest.rmdir()
                dest.symlink_to(other, target_is_directory=True)
            self.assertEqual(sync(dest, runner=runner, sleeper=sleeper),
                             'invalid_repository_after_command')
            self.assertEqual(len(calls), 1)
            self.assertTrue((other / '.dolt').is_dir())

    def test_destination_swapped_to_symlink_on_success_is_not_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            other = root / 'other'
            (other / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                dest.rmdir()
                dest.symlink_to(other, target_is_directory=True)
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')
            self.assertTrue((other / '.dolt').is_dir())

    def test_destination_swapped_to_symlink_on_os_error_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            other = root / 'other'
            (other / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                dest.rmdir()
                dest.symlink_to(other, target_is_directory=True)
                raise PermissionError('cannot execute')
            self.assertEqual(sync(dest, runner=runner),
                             'invalid_repository_after_command')
            self.assertTrue((other / '.dolt').is_dir())

    def test_destination_swapped_to_symlink_on_failed_pull_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / 'stocks'
            (dest / '.dolt').mkdir(parents=True)
            other = root / 'other'
            (other / '.dolt').mkdir(parents=True)
            def runner(cmd, **kwargs):
                (dest / '.dolt').rmdir()
                dest.rmdir()
                dest.symlink_to(other, target_is_directory=True)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')
            self.assertEqual(sync(dest, runner=runner, sleeper=lambda _: self.fail('no retry')),
                             'invalid_repository_after_command')
            self.assertTrue((other / '.dolt').is_dir())

class CliFreshnessTest(unittest.TestCase):
    def test_cached_fallback_is_not_reported_as_fresh_success(self):
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import us_dolt_sync

        for status in ('cached_after_rate_limit', 'cached_after_timeout',
                       'cached_after_os_error'):
            with self.subTest(status=status):
                output = io.StringIO()
                with patch('sys.argv', ['us_dolt_sync.py', '/tmp/unused-stocks']), \
                     patch.object(us_dolt_sync, 'sync', return_value=status), \
                     redirect_stdout(output):
                    with self.assertRaises(SystemExit) as raised:
                        us_dolt_sync.main()
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual(output.getvalue().strip(), status)

    def test_updated_cache_still_exits_successfully(self):
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        import us_dolt_sync

        output = io.StringIO()
        with patch('sys.argv', ['us_dolt_sync.py', '/tmp/unused-stocks']), \
             patch.object(us_dolt_sync, 'sync', return_value='updated'), \
             redirect_stdout(output):
            us_dolt_sync.main()
        self.assertEqual(output.getvalue().strip(), 'updated')


if __name__ == '__main__':
    unittest.main()
