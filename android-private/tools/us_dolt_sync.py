"""Conservative Dolt mirror synchronization. Never delete a working local clone."""
import argparse
import re
from pathlib import Path
import subprocess
import time

REMOTE = 'post-no-preference/stocks'
RATE_LIMIT = re.compile(r'(?<![A-Za-z0-9])429(?![A-Za-z0-9])|too many requests', re.I)


def _valid_metadata(destination):
    metadata = destination / '.dolt'
    return metadata.is_dir() and not metadata.is_symlink()


def sync(destination, *, runner=subprocess.run, sleeper=time.sleep, attempts=2):
    # Reject a symlink at the clone root before resolve() can follow it.
    # A linked destination must never redirect a pull into another directory.
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError('destination must not be a symlink')
    if attempts < 1 or attempts > 3:
        raise ValueError('attempts must be 1..3')
    if destination.exists() and not _valid_metadata(destination):
        raise ValueError('destination exists but is not a Dolt repository')
    if not destination.exists() and not destination.parent.is_dir():
        raise ValueError('destination parent does not exist')
    for attempt in range(attempts):
        # A previous pull/backoff may have lost its repository metadata.
        # Never turn the next retry into a clone over an existing directory.
        if destination.is_symlink() or (destination.exists() and not _valid_metadata(destination)):
            return 'invalid_repository_after_command'
        existing = _valid_metadata(destination)
        command = (['dolt', 'pull', '--ff-only'] if existing else
                   ['dolt', 'clone', '--depth', '1', REMOTE, destination.name])
        try:
            result = runner(command, cwd=str(destination if existing else destination.parent),
                            capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            if not existing and destination.exists():
                # Interrupted initial clones can leave partial files or metadata.
                # Preserve them for manual inspection instead of claiming a clean timeout.
                return 'partial_clone_requires_manual_cleanup'
            # A timeout can also leave an existing repository unusable.
            # Do not claim that a cache survived without checking its metadata.
            if existing and (destination.is_symlink() or not _valid_metadata(destination)):
                return 'invalid_repository_after_command'
            return 'cached_after_timeout' if existing else 'timed_out'
        except FileNotFoundError:
            return 'dolt_not_installed'
        except OSError:
            if not existing and destination.exists():
                return 'partial_clone_requires_manual_cleanup'
            # A runner may have removed the metadata before raising an OS error.
            # Never report a usable cache unless its directory still exists.
            if existing and (destination.is_symlink() or not _valid_metadata(destination)):
                return 'invalid_repository_after_command'
            return 'cached_after_os_error' if existing else 'os_error'
        if result.returncode == 0:
            if destination.is_symlink() or not _valid_metadata(destination):
                # A zero exit status alone does not establish a usable cache.
                # Do not report a successful refresh or attempt another clone.
                return 'invalid_repository_after_command'
            return 'updated' if existing else 'cloned'
        if existing and (destination.is_symlink() or not _valid_metadata(destination)):
            # A failed pull must not be reported as a usable cached repository.
            return 'invalid_repository_after_command'
        message = ((result.stderr or '') + '\n' + (result.stdout or '')).lower()
        rate_limited = bool(RATE_LIMIT.search(message))
        # A failed initial clone may leave a partial directory; do not retry it blindly.
        if not existing and destination.exists():
            # Failed clones may leave an incomplete directory. Never retry or
            # treat it as a cache; require explicit inspection before cleanup.
            return 'partial_clone_requires_manual_cleanup'
        if not rate_limited or attempt == attempts - 1 or not existing:
            return 'cached_after_rate_limit' if rate_limited and existing else ('rate_limited' if rate_limited else 'failed')
        sleeper(60 * (attempt + 1))
    raise AssertionError('unreachable')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    result = sync(args.destination)
    print(result)
    if result in ('failed', 'rate_limited', 'timed_out', 'dolt_not_installed', 'os_error', 'invalid_repository_after_command', 'partial_clone_requires_manual_cleanup'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
