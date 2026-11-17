"""Refresh the bundled Android JPX rights data from the official catalogs."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from jpx_android_rights_snapshot import snapshot
from jpx_daily_probe import CODE
from jpx_rights_sources import DAILY_INDEX, daily_sources, monthly_sources, official_url, page_links


def combine(previous, fresh):
    codes = set(fresh["coveredCodes"])
    notices = {}
    for entry in previous["notices"]:
        code, day, source = entry["code"], entry["exDay"], entry["source"]
        if not CODE.fullmatch(code) or not official_url(source) or date.fromisoformat(day).isoformat() != day:
            raise ValueError("Invalid notice in the existing Android JPX snapshot")
        if code in codes:
            notices[code, day] = source
    for entry in fresh["notices"]:
        notices[entry["code"], entry["exDay"]] = entry["source"]
    return {
        "coveredCodes": fresh["coveredCodes"],
        # Months must pass the current audit. A daily notice cannot certify a month.
        "monthlySources": fresh["monthlySources"],
        "notices": [{"code": code, "exDay": day, "source": source}
                    for (code, day), source in sorted(notices.items())],
    }


def refresh(path, first_month, last_month, *, dry_run=False, include_codes=()):
    original = path.read_text(encoding="utf-8")
    previous = json.loads(original)
    codes = set(previous["coveredCodes"]) | set(include_codes)
    if not codes or any(not CODE.fullmatch(code) for code in codes):
        raise ValueError("Invalid JPX codes in the existing snapshot or expansion list")

    with TemporaryDirectory() as download_dir:
        directory = Path(download_dir)
        daily, _, conflicts = daily_sources(page_links(DAILY_INDEX), directory)
        monthly, provenance, rejected, unpublished = monthly_sources(first_month, last_month, directory)
        if not daily or not monthly:
            raise ValueError("Expected official JPX daily workbooks and at least one verified monthly report")
        fresh = snapshot({"monthly_report_provenance": provenance, "daily_workbooks": daily},
                         directory, codes)
    merged = combine(previous, fresh)
    revision = previous.get("revision")
    previous_data = {key: value for key, value in previous.items() if key != "revision"}
    changed = merged != previous_data or revision is None
    if changed and not dry_run:
        updated_at = datetime.now(timezone.utc)
        if revision and updated_at <= datetime.fromisoformat(revision):
            raise ValueError("The new JPX snapshot revision must be later than the existing revision")
        merged = {"revision": updated_at.isoformat().replace("+00:00", "Z"), **merged}
        with TemporaryDirectory(dir=path.parent) as staging:
            replacement = Path(staging) / path.name
            replacement.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
            if path.read_text(encoding="utf-8") != original:
                raise ValueError("The Android JPX snapshot changed during refresh; run again")
            replacement.replace(path)
    return {
        "changed": changed,
        "dryRun": dry_run,
        "monthlyReportsVerified": len(monthly),
        "rejectedMonths": sorted(rejected),
        "unpublishedMonths": unpublished,
        "dailyWorkbooksVerified": len(daily),
        "conflictingDailyEventDates": conflicts["event_keys_with_conflicting_ex_dates"],
        "retainedNotices": len(merged["notices"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset", type=Path)
    parser.add_argument("--start-month", required=True, help="First month needed by the app, as YYYY-MM")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-code", action="append", default=[], help="Audit an additional JPX code")
    args = parser.parse_args()
    try:
        first_month = date.fromisoformat(args.start_month + "-01")
    except ValueError:
        parser.error("--start-month must use YYYY-MM")
    last_month = datetime.now(ZoneInfo("Asia/Tokyo")).date().replace(day=1)
    if first_month > last_month or first_month.year not in (last_month.year - 1, last_month.year):
        parser.error("--start-month must be within the current or previous catalog year")
    print(json.dumps(refresh(args.asset, first_month, last_month, dry_run=args.dry_run,
                             include_codes=args.include_code), indent=2))


if __name__ == "__main__":
    main()
