"""v34: retain at most 90 dated, source-backed SGX dashboard snapshots.

Never synthesize missing prices or interpolate market days.
The latest run for a UTC date replaces only that date's entry.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MAX_DAYS = 90
FIELDS = ("price_sgd", "per_reference", "pbr_reference_unverified",
          "market_cap_sgd", "quote_timestamp_utc", "quote_freshness",
          "shares_as_of_date", "quality_flags")


def iso_datetime(value):
    if not isinstance(value, str):
        raise ValueError("Missing ISO date")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must have timezone")
    return parsed.astimezone(timezone.utc)


def snapshot(feed):
    if feed.get("schema_version") != "value_hunter_web_v29":
        raise ValueError("Unsupported live feed schema")
    generated_at = iso_datetime(feed.get("updated_at_utc"))
    records = feed.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Missing records")
    names = set()
    points = []
    ranked = 0
    for row in records:
        symbol = row.get("symbol")
        if (not isinstance(symbol, str) or not symbol.isalnum()
                or len(symbol) > 8 or symbol in names
                or type(row.get("ranking_eligible")) is not bool):
            raise ValueError("Invalid symbol record")
        names.add(symbol)
        point = {"symbol": symbol}
        for field in FIELDS:
            point[field] = row.get(field)
        if row["ranking_eligible"]:
            ranked += 1
            point["ranking_eligible"] = True
            point["pbr_verified"] = row.get("pbr_verified")
        points.append(point)
    if feed.get("ranking_enabled") is not (ranked > 0) or feed.get("ranking_eligible_count") != ranked:
        raise ValueError("Unexpected ranking status")
    if ranked:
        validator = Path(__file__).resolve().parents[1] / "docs/sgx-ranking-validation.js"
        result = subprocess.run(
            ["node", "-e", r"""
const fs = require("node:fs");
const {checkFeed} = require(process.argv[1]);
const errors = checkFeed(JSON.parse(fs.readFileSync(0, "utf8")));
if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
}
""", str(validator)],
            input=json.dumps(feed), text=True, capture_output=True, check=False,
        )
        if result.returncode:
            raise ValueError("Ranked feed failed publication checks: " + result.stderr.strip())
    return {
        "date_utc": generated_at.date().isoformat(),
        "source_updated_at_utc": generated_at.isoformat(),
        "records": points,
        "quote_count": sum(isinstance(r.get("price_sgd"), (int, float))
                           and not isinstance(r.get("price_sgd"), bool) for r in points),
        "source": ("VALUE_HUNTER_AI_PUBLIC_FEED_WITH_RANKED_QUOTES" if ranked
                   else "VALUE_HUNTER_AI_PUBLIC_FEED_UNVERIFIED_QUOTES"),
    }


def build_index(existing, today, max_days=MAX_DAYS):
    if existing is not None and existing.get("schema_version") != "value_hunter_history_v34":
        raise ValueError("Incompatible history index")
    entries = {} if existing is None else {
        entry["date_utc"]: entry for entry in existing.get("entries", [])
    }
    for key in entries:
        if not isinstance(key, str) or len(key) != 10:
            raise ValueError("Bad historic date key")
    entries[today["date_utc"]] = today
    keys = sorted(entries, reverse=True)[:max_days]
    return {
        "schema_version": "value_hunter_history_v34",
        "note": "Daily snapshots without interpolated prices. Ranked rows are flagged individually.",
        "retained_days": len(keys),
        "latest_date_utc": keys[0],
        "entries": [entries[key] for key in sorted(keys)],
    }


def save(feed, history_dir):
    location = Path(history_dir)
    location.mkdir(parents=True, exist_ok=True)
    point = snapshot(feed)
    index_file = location / "index.json"
    existing = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else None
    index = build_index(existing, point)
    kept = {entry["date_utc"] for entry in index["entries"]}
    for file in location.glob("????-??-??.json"):
        if file.stem not in kept:
            file.unlink()
    (location / (point["date_utc"] + ".json")).write_text(
        json.dumps(point, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--history-dir", default="docs/data/history")
    args = parser.parse_args()
    feed = json.loads(Path(args.source).read_text(encoding="utf-8"))
    index = save(feed, args.history_dir)
    print(f"History: {index['retained_days']} dated snapshots, latest {index['latest_date_utc']}")


if __name__ == "__main__":
    main()
