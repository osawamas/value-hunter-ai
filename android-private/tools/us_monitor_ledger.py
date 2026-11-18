"""Build a private NYSE/Nasdaq SEC ledger and count coverage against a close snapshot."""

import argparse
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import json
import re
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory

from us_public_files_probe import (
    SEC_DIRECTORY,
    android_close_rows,
    fetch,
    issuers_requiring_class_review,
    load_listing_directories,
    read_sec_directory,
    validated_closes,
)

VENUES = {"NYSE", "Nasdaq"}
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/src/main/java/jp/valuehunter/privatewatch/UsFinancialFacts.java"


def universe(listings, sec):
    multiple = issuers_requiring_class_review(listings, sec)
    rows = []
    for symbol, (venue, kind) in sorted(listings.items()):
        if venue not in VENUES or kind != "common_or_ordinary_label":
            continue
        candidates = sec.get(symbol, set())
        if re.fullmatch(r"[A-Z]+\.[A-Z]", symbol):
            alias = symbol.replace(".", "-")
            if alias not in listings:
                candidates = candidates | sec.get(alias, set())
        matches = {cik for cik, exchange in candidates if exchange == venue}
        row = {"symbol": symbol, "exchange": venue}
        if len(matches) != 1:
            row["hold"] = "issuer_missing_or_ambiguous"
        else:
            cik = matches.pop()
            row["cik"] = cik
            if cik in multiple:
                row["hold"] = "multiple_listed_classes"
        rows.append(row)
    return rows


def counts(rows, prices):
    metrics = {}
    for venue in sorted(VENUES):
        scoped = [row for row in rows if row["exchange"] == venue]
        priced = [row for row in scoped if row["symbol"] in prices]
        covered = [row for row in priced if "shares" in row]
        ready = [row for row in covered if row["profit"] > 0 and row["equity"] > 0]
        metrics[venue] = {
            "listed": len(scoped), "with_daily_close": len(priced),
            "with_close_and_sec_issuer": sum("cik" in row for row in priced),
            "with_close_and_reference_financials": len(covered),
            "with_positive_profit_and_equity": len(ready),
            "financial_holds": dict(Counter(row["hold"] for row in priced if "hold" in row)),
        }
    return metrics


def reference_screen(rows, prices, session, fx, splits):
    if splits.get("query_execution_status") != "Success":
        raise ValueError("Incomplete split query")
    dates = {}
    for split in splits["rows"]:
        symbol, day = split["symbol"], date.fromisoformat(split["split_date"])
        if symbol in dates or not session - timedelta(days=150) <= day <= session:
            raise ValueError("Unexpected split query rows")
        dates[symbol] = day
    rates = {date.fromisoformat(row["date"]): Decimal(str(row["rate"]))
             for row in fx if row["base"] == "USD" and row["quote"] == "JPY"}
    available = [day for day, value in rates.items() if session - timedelta(days=4) <= day <= session
                 and value.is_finite() and value > 0]
    if not available:
        raise ValueError("No recent USD/JPY rate on or before the US trading date")
    fx_day = max(available)
    fx_rate = rates[fx_day]
    summary = {"fx_date": fx_day.isoformat(), "exchanges": {}}
    for venue in sorted(VENUES):
        reasons = Counter()
        for row in rows:
            symbol = row["symbol"]
            if row["exchange"] != venue or symbol not in prices or "shares" not in row:
                continue
            if symbol in dates and dates[symbol] >= date.fromisoformat(row["share_date"]):
                reasons["hold_split"] += 1
                continue
            price = Decimal(str(prices[symbol]))
            yen = price * fx_rate
            if yen > 100_000:
                reasons["outside_budget"] += 1
                continue
            earnings, equity = Decimal(str(row["profit"])), Decimal(str(row["equity"]))
            if earnings <= 0 or equity <= 0:
                reasons["hold_nonpositive_profit_or_equity"] += 1
                continue
            cap = price * Decimal(str(row["shares"]))
            per_ok, pbr_ok = cap <= 15 * earnings, cap <= equity
            if per_ok and pbr_ok:
                reasons["priority"] += 1
            elif per_ok and cap <= Decimal("1.5") * equity or pbr_ok and cap <= 20 * earnings:
                reasons["reference"] += 1
            else:
                reasons["outside_valuation"] += 1
        summary["exchanges"][venue] = dict(reasons)
    return summary


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("trading_date", type=date.fromisoformat)
    cli.add_argument("--close-cache", type=Path, required=True)
    cli.add_argument("--companyfacts", type=Path)
    cli.add_argument("--json-jar", type=Path)
    cli.add_argument("--directory-cache", type=Path)
    cli.add_argument("--sec-directory", type=Path)
    cli.add_argument("--fx-snapshot", type=Path)
    cli.add_argument("--split-snapshot", type=Path)
    cli.add_argument("--output", type=Path, required=True, help="Private output JSON used by the Android build")
    options = cli.parse_args()
    if bool(options.companyfacts) != bool(options.json_jar):
        cli.error("--companyfacts and --json-jar are used together")
    if bool(options.fx_snapshot) != bool(options.split_snapshot):
        cli.error("--fx-snapshot and --split-snapshot are used together")
    observed, listings, _ = load_listing_directories(options.directory_cache)
    sec_content = options.sec_directory.read_bytes() if options.sec_directory else fetch(SEC_DIRECTORY)
    sec = read_sec_directory(sec_content)
    rows = universe(listings, sec)
    _, prices = validated_closes(options.trading_date,
                                 android_close_rows(options.close_cache, options.trading_date, dolt=True))
    ledger = {"trading_date_et": options.trading_date.isoformat(), "listing_observed_et": observed,
              "listings": rows}
    if options.companyfacts:
        with TemporaryDirectory(prefix="us-bulk-ledger-") as build:
            subprocess.run(["javac", "--release", "17", "-cp", str(options.json_jar), "-d", build,
                            str(SOURCE), str(ROOT / "tools/UsBulkLedger.java")], check=True)
            result = subprocess.run(["java", "-Xmx768m", "-cp", f"{build}:{options.json_jar}",
                                     "jp.valuehunter.privatewatch.UsBulkLedger",
                                     str(options.companyfacts), ledger["trading_date_et"]],
                                    input=json.dumps(ledger).encode(), stdout=subprocess.PIPE, check=True)
            ledger = json.loads(result.stdout)
    else:
        for row in rows:
            row.setdefault("hold", "companyfacts_archive_not_loaded")
    metrics = counts(ledger["listings"], prices)
    if options.fx_snapshot:
        metrics["reference_screen"] = reference_screen(ledger["listings"], prices, options.trading_date,
                                                        json.loads(options.fx_snapshot.read_bytes()),
                                                        json.loads(options.split_snapshot.read_bytes()))
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=options.output.parent, delete=False) as staging:
        temporary = Path(staging.name)
        try:
            json.dump(ledger, staging, separators=(",", ":"))
            staging.write("\n")
            staging.close()
            temporary.replace(options.output)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
