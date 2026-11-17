"""Capture the midday US listing pair and check the prior session's saved pair."""
import argparse
from datetime import datetime, time, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from us_dolt_sync import sync
from us_public_files_probe import (
    coverage,
    dolt_rows,
    listing_snapshot_assessment,
    load_listing_directories,
    require_listing_date,
    save_listing_snapshot,
)

EASTERN = ZoneInfo("America/New_York")


def run_cycle(archive, prices, now, calendar):
    eastern_now = now.astimezone(EASTERN)
    today = eastern_now.date()
    result = {"checked_at": eastern_now.isoformat()}
    if not calendar.is_session(today.isoformat()) or not time(12) <= eastern_now.time() < time(13):
        return dict(result, status="outside_capture_window")

    target = archive / today.isoformat()
    if target.is_dir():
        observed, _, _ = load_listing_directories(target)
        require_listing_date(today, observed)
        result["capture"] = "already_saved"
    else:
        observed, _, originals = load_listing_directories()
        require_listing_date(today, observed)
        result["capture"] = save_listing_snapshot(archive, today, originals)

    start, end = today - timedelta(days=7), today - timedelta(days=1)
    pending = []
    for session in calendar.sessions_in_range(start.isoformat(), end.isoformat()):
        day = session.date()
        snapshot = archive / day.isoformat()
        if snapshot.is_dir() and not (snapshot / "dolt-coverage.json").is_file():
            pending.append((day, snapshot))
    if not pending:
        return dict(result, status="no_pending_snapshots")

    sync_state = sync(prices)
    result["dolt_sync"] = sync_state
    if sync_state not in ("updated", "cloned", "cached_after_timeout", "cached_after_rate_limit"):
        return dict(result, status="dolt_unavailable")
    sessions = []
    for day, snapshot in pending:
        try:
            outcome = compare_session(day, snapshot, prices, sync_state)
        except (OSError, ValueError, KeyError) as error:
            outcome = {"status": "comparison_failed", "error": str(error)}
        sessions.append(dict(outcome, trading_date=day.isoformat()))
    return dict(result, status="checked_pending_snapshots", sessions=sessions)


def compare_session(prior, snapshot, prices, sync_state):
    report_path = snapshot / "dolt-coverage.json"
    observed, listings, _ = load_listing_directories(snapshot)
    require_listing_date(prior, observed)
    prices_on_day = dolt_rows(prices, prior)
    if not any(row["close"] is not None for row in prices_on_day):
        return {"status": "no_dolt_closes_for_session"}
    report = coverage(prior, listings, prices_on_day, price_basis="Dolt reported close (basis under evaluation)")
    report["directory_observed_at"] = observed
    report["listing_snapshot_assessment"] = listing_snapshot_assessment(prior, observed)
    report["dolt_sync"] = sync_state
    with TemporaryDirectory(prefix=".coverage-", dir=snapshot) as directory:
        draft = Path(directory) / report_path.name
        draft.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        draft.replace(report_path)
    return {"status": "compared", "report": str(report_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--dolt-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        import exchange_calendars
    except ImportError:
        parser.exit(1, "Install exchange-calendars>=4.7,<5 in the scheduled Python environment.\n")
    try:
        result = run_cycle(args.archive.resolve(), args.dolt_dir.resolve(),
                           datetime.now(EASTERN), exchange_calendars.get_calendar("XNYS"))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"US daily coverage: {error}\n")
    print(json.dumps(result))
    if result["status"] == "dolt_unavailable" or any(
        day["status"] != "compared" for day in result.get("sessions", ())
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
