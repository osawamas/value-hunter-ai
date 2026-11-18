"""Refresh the private SEC ledger and copy it to a connected Android debug build."""

import argparse
from contextlib import contextmanager
import fcntl
from datetime import date, timedelta
from hashlib import sha256
import json
import re
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from zipfile import ZipFile

from us_monitor_ledger import main as build_ledger
from us_public_files_probe import fetch

PACKAGE = "jp.valuehunter.privatewatch"
SEC_BULK = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
DOLT = "https://www.dolthub.com/api/v1alpha1/post-no-preference/stocks"
FX = "https://api.frankfurter.dev/v2/rates"
MAX_PRIVATE_FILE = 16 * 1024 * 1024


@contextmanager
def exclusive(directory):
    with (directory / "sync.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def refresh_companyfacts(cache, staged, user_agent):
    command = ["curl", "--fail", "--silent", "--show-error", "--proto", "=https",
               "--connect-timeout", "20", "--max-time", "1200", "--max-filesize", "3000000000",
               "--user-agent", user_agent, "--remote-time", "--output", str(staged),
               "--write-out", "%{http_code}"]
    if cache.is_file():
        command += ["--time-cond", str(cache)]
    result = subprocess.run([*command, SEC_BULK], check=True, capture_output=True, text=True)
    if result.stdout == "304" and cache.is_file():
        return
    if result.stdout != "200":
        raise ValueError("Unexpected SEC bulk download status")
    with ZipFile(staged) as archive:
        if archive.getinfo("CIK0000320193.json").file_size <= 0 or len(archive.infolist()) < 1000:
            raise ValueError("Incomplete SEC companyfacts archive")
    staged.replace(cache)


def get_splits(session):
    start = session - timedelta(days=150)
    where = f" WHERE ex_date BETWEEN '{start}' AND '{session}'"

    def query(sql):
        return json.loads(fetch(DOLT + "?" + urlencode({"q": sql})))

    manifest = query("SELECT DOLT_HASHOF('HEAD') AS revision")
    if manifest.get("query_execution_status") != "Success" or len(manifest["rows"]) != 1:
        raise ValueError("Split revision unavailable")
    revision = manifest["rows"][0]["revision"]
    if not re.fullmatch(r"[0-9a-v]{32}", revision):
        raise ValueError("Invalid split revision")

    results = []
    seen = set()
    # SQL API limits each response to 1,000 rows. Continue when at the limit.
    for offset in range(0, 12_000, 1000):
        page = f" OFFSET {offset}" if offset else ""
        response = query("SELECT act_symbol AS symbol, CAST(MAX(ex_date) AS CHAR) AS split_date"
                         f" FROM split AS OF '{revision}'{where}"
                         f" GROUP BY act_symbol ORDER BY act_symbol LIMIT 1000{page}")
        rows = response["rows"]
        if response.get("query_execution_status") != "Success" or len(rows) > 1000:
            raise ValueError("Incomplete split history")
        for row in rows:
            symbol = row["symbol"]
            if not re.fullmatch(r"[A-Z0-9.$+^=/_-]{1,24}", symbol) or symbol in seen:
                raise ValueError("Unexpected or duplicate split symbol")
            seen.add(symbol)
        results.extend(rows)
        if len(rows) < 1000:
            return {"query_execution_status": "Success", "rows": results}
    raise ValueError("Split history exceeded the page limit")


def sync(adb, directory, jar, user_agent):
    def device(*args, **kwargs):
        return subprocess.run([adb, *args], check=True, timeout=60, **kwargs)

    with TemporaryDirectory(prefix=".sync-", dir=directory) as work:
        work = Path(work)
        closes = work / "closes.json"
        with closes.open("wb") as file:
            device("exec-out", "run-as", PACKAGE, "cat", "no_backup/us-daily-closes.json", stdout=file)
        if not 0 < closes.stat().st_size <= MAX_PRIVATE_FILE:
            raise ValueError("Android close snapshot is missing or oversized")
        close_bytes = closes.read_bytes()
        session = date.fromisoformat(json.loads(close_bytes)["trading_date_et"])
        digest = sha256(close_bytes).hexdigest()
        archive = directory / "companyfacts.zip"
        receipt = directory / "synced-close.sha256"
        if receipt.is_file() and receipt.read_text(encoding="ascii").strip() == digest:
            print(f"SEC ledger already synced for {session}")
            return
        refresh_companyfacts(archive, work / "companyfacts.zip", user_agent)
        fx = work / "fx.json"
        fx_search = urlencode({"base": "USD", "quotes": "JPY",
                               "from": session - timedelta(days=4), "to": session})
        splits = work / "splits.json"
        ledger = work / "ledger.json"
        args = [str(session), "--close-cache", str(closes), "--companyfacts", str(archive),
                "--json-jar", str(jar), "--output", str(ledger)]
        try:
            fx.write_bytes(fetch(FX + "?" + fx_search))
            splits.write_text(json.dumps(get_splits(session)), encoding="utf-8")
            build_ledger(args + ["--fx-snapshot", str(fx), "--split-snapshot", str(splits)])
            screened = True
        except (ValueError, KeyError):
            print("Reference screen pending. Syncing financials and retrying the screen next run.")
            build_ledger(args)
            screened = False
        if not 0 < ledger.stat().st_size <= MAX_PRIVATE_FILE:
            raise ValueError("Generated SEC ledger is missing or oversized")
        # A failed or interrupted copy leaves the current ledger available.
        with ledger.open("rb") as file:
            device("shell", "-T",
                   f"run-as {PACKAGE} sh -c 'umask 077 && cat > no_backup/us-monitor-incoming.tmp'",
                   stdin=file)
        device("shell", "run-as", PACKAGE, "mv", "no_backup/us-monitor-incoming.tmp",
               "no_backup/us-monitor-universe.json")
        if screened:
            staged_receipt = work / receipt.name
            staged_receipt.write_text(digest + "\n", encoding="ascii")
            staged_receipt.replace(receipt)
        print(f"Private SEC ledger synced for {session}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb", help="Android SDK adb path")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--json-jar", type=Path, required=True)
    parser.add_argument("--sec-user-agent", required=True, help="SEC application name and contact email")
    options = parser.parse_args()
    if not options.json_jar.is_file():
        parser.error("--json-jar must identify the org.json JAR")
    options.cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    with exclusive(options.cache) as acquired:
        if acquired:
            sync(options.adb, options.cache, options.json_jar.resolve(), options.sec_user_agent)


if __name__ == "__main__":
    main()
