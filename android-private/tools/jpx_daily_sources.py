"""Retrieve the latest published JPX stock-price daily PDF for local validation."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

from jpx_rights_sources import download
from jpx_valuation_probe import trading_date

REPORT_LIMIT = 32_000_000
REPORT_ROOT = "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files"


def latest_report(today, output):
    # JPX publishes the report on the next business day. Search recent trading dates.
    for days_ago in range(1, 11):
        day = today - timedelta(days=days_ago)
        if day.weekday() >= 5:
            continue
        url = f"{REPORT_ROOT}/{day:%Y%m}/stq_{day:%Y%m%d}.pdf"
        try:
            body = download(url, limit=REPORT_LIMIT)
        except HTTPError as error:
            if error.code != 404:
                raise
            continue
        # Validate the official trading date in the document before replacing the output.
        with TemporaryDirectory(dir=output.parent) as staging:
            temporary = Path(staging) / output.name
            temporary.write_bytes(body)
            if trading_date(temporary) != day:
                raise ValueError(f"JPX daily report date does not match {day.isoformat()}")
            temporary.replace(output)
        return day, url
    raise ValueError("No recent JPX stock-price daily report was found")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    report_day, url = latest_report(today, args.output)
    print(f"Latest published JPX stock-price report: {report_day} ({url})")


if __name__ == "__main__":
    main()
