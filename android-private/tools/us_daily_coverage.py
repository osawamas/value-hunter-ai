"""Capture the midday US listing pair and recheck recent saved US listing pairs."""
import argparse
from datetime import datetime, time, timedelta
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile
from zoneinfo import ZoneInfo

from us_dolt_sync import sync
from us_public_files_probe import (
    DIA_HOLDINGS,
    SAMPLE,
    SYMBOL,
    coverage,
    dolt_rows,
    fetch,
    listing_snapshot_assessment,
    load_dia,
    load_listing_directories,
    parquet_rows,
    require_listing_date,
    save_listing_snapshot,
    validated_closes,
)

EASTERN = ZoneInfo("America/New_York")
FOCUS_MARKETS = ("NYSE", "Nasdaq")
MARKET_COUNTS = "common_or_ordinary_label_by_exchange"
MISSING_SYMBOLS = "missing_close_symbols_by_exchange"
DIA_ERRORS = (BadZipFile, ImportError, KeyError, OSError, ParseError, ValueError)


def archive_dia_holdings(directory, today):
    content = fetch(DIA_HOLDINGS)
    as_of, _ = load_dia(content)
    if as_of > today:
        raise ValueError("DIA holdings date is in the future")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{as_of}.xlsx"
    if path.is_file() and path.read_bytes() == content:
        return {"status": "already_saved", "as_of": as_of.isoformat()}
    with TemporaryDirectory(prefix=".dia-", dir=directory) as temporary:
        draft = Path(temporary) / path.name
        draft.write_bytes(content)
        draft.replace(path)
    return {"status": "saved", "as_of": as_of.isoformat()}


def dia_for_session(directory, day):
    path = directory / f"{day}.xlsx"
    if not path.is_file():
        return None, "no_same_date_holdings"
    try:
        holdings = load_dia(path.read_bytes())
        if holdings[0] != day:
            return None, "holdings_date_mismatch"
    except DIA_ERRORS:
        return None, "holdings_unreadable"
    return holdings, "same_date_holdings"


def run_cycle(archive, prices, now, calendar, *, with_dow=False, compare_marketparquet=False):
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

    dia_directory = archive / "dia-holdings" if with_dow else None
    if dia_directory is not None:
        try:
            result["dia_capture"] = archive_dia_holdings(dia_directory, today)
        except DIA_ERRORS as error:
            result["dia_capture"] = {"status": "unavailable", "error": str(error)}

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
            outcome = compare_session(
                day, snapshot, prices, sync_state, eastern_now,
                dia_directory=dia_directory, compare_marketparquet=compare_marketparquet,
            )
        except (OSError, ValueError, KeyError) as error:
            outcome = {"status": "comparison_failed", "error": str(error)}
        sessions.append(dict(outcome, trading_date=day.isoformat()))
    return dict(result, status="checked_recent_snapshots", sessions=sessions)


def compare_missing_symbols(previous, current, market, previous_count, current_count):
    previous_lists = previous.get(MISSING_SYMBOLS)
    current_list = current[MISSING_SYMBOLS][market]
    old_list = previous_lists.get(market) if isinstance(previous_lists, dict) else None
    if (not isinstance(old_list, list) or len(old_list) != previous_count
            or any(not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) for symbol in old_list)
            or len(set(old_list)) != len(old_list) or len(current_list) != current_count):
        return {}
    old, new = set(old_list), set(current_list)
    return {"recovered_symbols": sorted(old - new), "newly_missing_symbols": sorted(new - old)}


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
    # Never compare legacy reports without content hashes to a hashed snapshot:
    # matching observation timestamps do not prove that the listing set is unchanged.
    if previous.get("directory_sha256") != current.get("directory_sha256"):
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
        if previous.get("directory_sha256") and MISSING_SYMBOLS in current:
            changes[market].update(compare_missing_symbols(
                previous, current, market, new["listed"] - old_count, new["without_close"]
            ))
    if not changes:
        return {"status": "no_comparable_markets"}
    return {
        "status": "compared",
        "previous_checked_at": previous.get("checked_at"),
        "markets": changes,
    }


def compare_session(prior, snapshot, prices, sync_state, checked_at, *, dia_directory=None, compare_marketparquet=False):
    report_path = snapshot / "dolt-coverage.json"
    replaces_report = report_path.is_file()
    observed, listings, originals = load_listing_directories(snapshot)
    require_listing_date(prior, observed)
    prices_on_day = dolt_rows(prices, prior)
    if not any(row["close"] is not None for row in prices_on_day):
        return {"status": "no_dolt_closes_for_session", "previous_report_retained": replaces_report}
    holdings, dia_status = dia_for_session(dia_directory, prior) if dia_directory is not None else (None, None)
    reference_bars = None
    reference_status = None
    if compare_marketparquet:
        try:
            candidate = parquet_rows(fetch(SAMPLE + prior.isoformat() + ".parquet"))
            _, reference_closes = validated_closes(prior, candidate)
            if not reference_closes:
                raise ValueError("No valid closes in the comparison sample")
            reference_bars = candidate
            reference_status = {"status": "compared", "price_basis": "split-adjusted"}
        except (ImportError, KeyError, OSError, ValueError, TypeError, NotImplementedError) as error:
            reference_status = {"status": "unavailable", "error": str(error)}
    report = coverage(prior, listings, prices_on_day, dow=holdings, comparison_bars=reference_bars,
                      price_basis="Dolt reported close (basis under evaluation)", include_missing_symbols=True)
    if reference_status is not None:
        report["marketparquet_reference"] = reference_status
    if dia_status is not None:
        report["dia_holdings_status"] = dia_status
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
    if reference_status is not None:
        outcome["marketparquet_reference"] = reference_status
        if reference_bars is not None:
            outcome["marketparquet_only_by_exchange"] = {
                market: details["only_marketparquet"]
                for market, details in report["dolt_marketparquet_comparison"].items()
                if market in FOCUS_MARKETS
            }
    if dia_status is not None:
        outcome["dia_holdings_status"] = dia_status
        if holdings is not None:
            outcome["dia_holdings_comparison"] = report["dia_holdings_comparison"]
    if replaces_report:
        outcome["previous_observation"] = report["previous_observation"]
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--dolt-dir", type=Path, required=True)
    parser.add_argument("--with-dow", action="store_true", help="Archive dated DIA holdings and check Dow coverage")
    parser.add_argument("--compare-marketparquet", action="store_true", help="Compare with the same-date public sample")
    args = parser.parse_args()
    try:
        import exchange_calendars
    except ImportError:
        parser.exit(1, "Install exchange-calendars>=4.7,<5 in the scheduled Python environment.\n")
    try:
        result = run_cycle(
            args.archive.resolve(), args.dolt_dir.resolve(), datetime.now(EASTERN),
            exchange_calendars.get_calendar("XNYS"), with_dow=args.with_dow,
            compare_marketparquet=args.compare_marketparquet,
        )
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"US daily coverage: {error}\n")
    print(json.dumps(result))
    if result["status"] == "dolt_unavailable" or any(
        day["status"] not in ("compared", "refreshed") for day in result.get("sessions", ())
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
