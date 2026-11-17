"""Capture the midday US listing pair and recheck recent saved US listing pairs."""
import argparse
from datetime import datetime, time, timedelta
from hashlib import sha256
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
FOCUS_MARKETS = ("NYSE", "Nasdaq")
MARKET_COUNTS = "common_or_ordinary_label_by_exchange"


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
    snapshots = []
    for session in calendar.sessions_in_range(start.isoformat(), end.isoformat()):
        day = session.date()
        snapshot = archive / day.isoformat()
        if snapshot.is_dir():
            snapshots.append((day, snapshot))
    if not snapshots:
        return dict(result, status="no_recent_snapshots")

    sync_state = sync(prices)
    result["dolt_sync"] = sync_state
    if sync_state not in ("updated", "cloned", "cached_after_timeout", "cached_after_rate_limit"):
        return dict(result, status="dolt_unavailable")
    sessions = []
    for day, snapshot in snapshots:
        try:
            outcome = compare_session(day, snapshot, prices, sync_state, eastern_now)
        except (OSError, ValueError, KeyError) as error:
            outcome = {"status": "comparison_failed", "error": str(error)}
        sessions.append(dict(outcome, trading_date=day.isoformat()))
    return dict(result, status="checked_recent_snapshots", sessions=sessions)


def compare_previous_report(path, current):
    """Compare the observed counts only when the archived directory still matches."""
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"status": "previous_report_unreadable"}
    if not isinstance(previous, dict) or any(
        current[key] != previous.get(key) for key in ("trading_date", "directory_observed_at", "sample_price_basis")
    ):
        return {"status": "different_report_basis"}
    if "directory_sha256" in previous and previous["directory_sha256"] != current.get("directory_sha256"):
        return {"status": "different_report_basis"}
    previous_markets = previous.get(MARKET_COUNTS)
    if not isinstance(previous_markets, dict):
        return {"status": "previous_market_counts_unavailable"}
    changes = {}
    for market in FOCUS_MARKETS:
        old = previous_markets.get(market)
        new = current[MARKET_COUNTS].get(market)
        if not isinstance(old, dict) or not new or old.get("listed") != new["listed"]:
            continue
        old_count = old.get("with_close")
        if type(old_count) is not int or not 0 <= old_count <= new["listed"]:
            continue
        delta = new["with_close"] - old_count
        changes[market] = {
            "previous_with_close": old_count,
            "current_with_close": new["with_close"],
            "change_in_with_close": delta,
        }
    if not changes:
        return {"status": "no_comparable_markets"}
    return {
        "status": "compared",
        "previous_checked_at": previous.get("checked_at"),
        "markets": changes,
    }


def compare_session(prior, snapshot, prices, sync_state, checked_at):
    report_path = snapshot / "dolt-coverage.json"
    replaces_report = report_path.is_file()
    observed, listings, originals = load_listing_directories(snapshot)
    require_listing_date(prior, observed)
    prices_on_day = dolt_rows(prices, prior)
    if not any(row["close"] is not None for row in prices_on_day):
        return {"status": "no_dolt_closes_for_session", "previous_report_retained": replaces_report}
    report = coverage(prior, listings, prices_on_day, price_basis="Dolt reported close (basis under evaluation)")
    report["directory_observed_at"] = observed
    report["directory_sha256"] = {name: sha256(content).hexdigest() for name, content in originals.items()}
    report["listing_snapshot_assessment"] = listing_snapshot_assessment(prior, observed)
    report["dolt_sync"] = sync_state
    report["coverage_status"] = "observed_unverified"
    report["checked_at"] = checked_at.isoformat()
    if replaces_report:
        report["previous_observation"] = compare_previous_report(report_path, report)
    with TemporaryDirectory(prefix=".coverage-", dir=snapshot) as directory:
        draft = Path(directory) / report_path.name
        draft.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        draft.replace(report_path)
    by_exchange = report[MARKET_COUNTS]
    outcome = {
        "status": "refreshed" if replaces_report else "compared",
        "report": str(report_path),
        MARKET_COUNTS: {
            venue: by_exchange[venue] for venue in FOCUS_MARKETS if venue in by_exchange
        },
    }
    if replaces_report:
        outcome["previous_observation"] = report["previous_observation"]
    return outcome


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
        day["status"] not in ("compared", "refreshed") for day in result.get("sessions", ())
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
