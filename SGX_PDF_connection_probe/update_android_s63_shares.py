"""Add a date-specific, issuer-verified SGXNet disclosure to the Android ledger."""
import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from sgx_s63_buyback_v109 import SYMBOL, fetch, parse_notice

SGT = timezone(timedelta(hours=8))
SOURCE = re.compile(r"https://links[.]sgx[.]com/1[.]0[.]0/corporate-announcements/[A-Z0-9]+/[a-f0-9]{64}")


def validate_record(row):
    day = date.fromisoformat(row["date"])
    disclosed = datetime.fromisoformat(row["disclosed_at"])
    if (day.isoformat() != row["date"] or disclosed.date() != day
            or disclosed.utcoffset() != timedelta(hours=8)
            or type(row["shares"]) is not int or not 0 < row["shares"] <= 10_000_000_000
            or not SOURCE.fullmatch(row["source"])):
        raise ValueError("Invalid date, count or official source in S63 ledger")


def update_ledger(path, urls, downloader=fetch):
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("schema") != 1 or ledger.get("symbol") != SYMBOL:
        raise ValueError("Unexpected S63 ledger schema")
    by_date = {}
    for row in ledger["records"]:
        validate_record(row)
        if row["date"] in by_date:
            raise ValueError(f"Duplicate S63 date: {row['date']}")
        by_date[row["date"]] = row

    added = []
    for url in dict.fromkeys(urls):
        if not SOURCE.fullmatch(url):
            raise ValueError("Expected the full official SGXNet document URL")
        notice = parse_notice(downloader(url), url)
        broadcast = datetime.strptime(notice["broadcast_sgt_text"], "%d-%b-%Y %H:%M:%S")
        row = {
            "date": notice["purchase_date"],
            "shares": notice["issued_excluding_treasury_after_purchase"],
            "source": notice["source_url"],
            "disclosed_at": broadcast.replace(tzinfo=SGT).isoformat(),
        }
        validate_record(row)
        if date.fromisoformat(row["date"]) > datetime.now(SGT).date():
            raise ValueError("Future S63 disclosure date")
        existing = by_date.get(row["date"])
        if existing is not None:
            if any(existing[field] != value for field, value in row.items()):
                raise ValueError(f"Conflicting S63 disclosure for {row['date']}")
            continue
        by_date[row["date"]] = row
        added.append(row["date"])

    if added:
        ledger["records"] = [by_date[day] for day in sorted(by_date)]
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
                temporary = Path(file.name)
                json.dump(ledger, file, indent=2)
                file.write("\n")
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return sorted(added)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("docs/data/android-s63-shares.json"))
    parser.add_argument("url", nargs="+")
    args = parser.parse_args()
    try:
        added = update_ledger(args.ledger, args.url)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"S63 ledger update rejected: {error}\n")
    print("Registered S63 dates: " + ", ".join(added) if added else "S63 ledger already up to date")


if __name__ == "__main__":
    main()
