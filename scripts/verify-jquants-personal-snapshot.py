#!/usr/bin/env python3
"""Verify a personal J-Quants CSV against its provenance receipt, entirely offline."""
import argparse
import csv
import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

FIELDS = ['market_id', 'date', 'currency', 'close']

def validate(csv_path, receipt_path):
    raw = Path(csv_path).read_bytes()
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    if not isinstance(receipt, dict) or receipt.get('provider') != 'J-Quants' or receipt.get('purpose') != 'personal' or receipt.get('price_basis') != 'unadjusted_close':
        raise ValueError('receipt provider, purpose or price basis is invalid')
    if hashlib.sha256(raw).hexdigest() != receipt.get('csv_sha256'):
        raise ValueError('CSV SHA-256 differs from receipt')
    period = receipt.get('requested_period')
    if not isinstance(period, dict):
        raise ValueError('missing requested period')
    first, last = period.get('first'), period.get('last')
    for day in (first, last):
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError('invalid receipt date')
    if first > last:
        raise ValueError('reversed requested period')
    codes = receipt.get('requested_codes')
    if not isinstance(codes, list) or not codes or len(set(codes)) != len(codes) or any(not isinstance(c, str) or not re.fullmatch(r'[0-9][0-9A-Z]{3}', c) for c in codes):
        raise ValueError('invalid requested codes')
    if not isinstance(receipt.get('observations'), int) or isinstance(receipt['observations'], bool):
        raise ValueError('invalid observation count')
    reader = csv.DictReader(raw.decode('utf-8-sig').splitlines(), strict=True)
    if reader.fieldnames != FIELDS:
        raise ValueError('unexpected CSV columns')
    seen, observed, count = set(), set(), 0
    for row in reader:
        if None in row or any(row.get(field) is None for field in FIELDS):
            raise ValueError('malformed CSV row')
        identifier, day, currency = row['market_id'], row['date'], row['currency']
        if not identifier.startswith('JP:') or identifier[3:] not in codes or currency != 'JPY':
            raise ValueError('unexpected security or currency')
        if date.fromisoformat(day).isoformat() != day or not first <= day <= last:
            raise ValueError('observation outside requested period')
        try:
            close = float(row['close'])
        except ValueError as exc:
            raise ValueError('invalid close') from exc
        if not math.isfinite(close) or close <= 0:
            raise ValueError('invalid close')
        key = (identifier, day)
        if key in seen:
            raise ValueError('duplicate security/date')
        seen.add(key)
        observed.add(identifier[3:])
        count += 1
    if count != receipt['observations'] or not count:
        raise ValueError('observation count mismatch or empty snapshot')
    if set(codes) != observed:
        raise ValueError('missing requested security')
    result = {'verified': True, 'observations': count, 'codes': sorted(observed), 'csv_sha256': receipt['csv_sha256']}
    if 'retrieved_at_utc' in receipt:
        stamp = receipt['retrieved_at_utc']
        if not isinstance(stamp, str) or not re.fullmatch(
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', stamp):
            raise ValueError('invalid UTC retrieval timestamp')
        retrieved = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        result['retrieved_at_utc'] = retrieved.astimezone(timezone.utc).isoformat(timespec='microseconds')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.csv, args.receipt), ensure_ascii=False))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, csv.Error) as exc:
        parser.exit(1, f'Snapshot verification failed: {exc}\n')

if __name__ == '__main__':
    main()
