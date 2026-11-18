"""Regression tests for Dolt cache integrity after subprocess completion."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from us_dolt_sync import sync


class DoltCacheIntegrityTest(unittest.TestCase):
    def test_failed_pull_replaced_metadata_symlink_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / 'stocks'
            (destination / '.dolt').mkdir(parents=True)
            other = root / 'other'
            other.mkdir()
            (destination / 'marker').write_text('preserve')
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                (destination / '.dolt').rmdir()
                (destination / '.dolt').symlink_to(other, target_is_directory=True)
                return SimpleNamespace(returncode=1, stderr='HTTP 429', stdout='')

            self.assertEqual(sync(destination, runner=runner,
                                  sleeper=lambda _: self.fail('must not retry')),
                             'invalid_repository_after_command')
            self.assertEqual(len(calls), 1)
            self.assertEqual((destination / 'marker').read_text(), 'preserve')
            self.assertTrue(other.is_dir())

    def test_successful_pull_replaced_metadata_symlink_is_not_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / 'stocks'
            (destination / '.dolt').mkdir(parents=True)
            other = root / 'other'
            other.mkdir()

            def runner(command, **kwargs):
                (destination / '.dolt').rmdir()
                (destination / '.dolt').symlink_to(other, target_is_directory=True)
                return SimpleNamespace(returncode=0, stderr='', stdout='')

            self.assertEqual(sync(destination, runner=runner),
                             'invalid_repository_after_command')
            self.assertTrue(other.is_dir())


if __name__ == '__main__':
    unittest.main()
