"""Check one unadjusted US close using an explicitly configured free FinzData plan."""
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import io
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://api.finzdata.com/v1"
SYMBOL = "AAPL"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read(path, key, query=None):
    url = BASE + path + ("?" + urlencode(query) if query else "")
    request = Request(url, headers={"X-API-Key": key})
    try:
        with build_opener(NoRedirect()).open(request, timeout=12) as response:
            body = response.read(32_769)
    except HTTPError as error:
        error.close()
        raise HTTPError(BASE, error.code, "FinzData request failed", None, None) from None
    if len(body) > 32_768:
        raise ValueError("Oversized FinzData response")
    return body


def exact_close(body, target):
    dates = set()
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        session = date.fromisoformat(row["date"])
        if row.get("symbol", SYMBOL) != SYMBOL or session != target or session in dates:
            raise ValueError("Unexpected symbol, date or duplicate bar")
        close = Decimal(row["close"])
        if not close.is_finite() or close <= 0:
            raise ValueError("Invalid close")
        dates.add(session)
    return target in dates


def audit(target, key, fetch=read):
    report = {"source": "finzdata_free_eod", "symbol": SYMBOL, "target_session": target.isoformat()}
    if not key:
        return {**report, "status": "key_unconfigured"}
    try:
        account = json.loads(fetch("/me", key))
        if account.get("plan") != "free":
            return {**report, "status": "free_plan_unverified"}
        body = fetch("/prices/daily", key, {"symbol": SYMBOL, "start": target.isoformat(),
                     "end": target.isoformat(), "adjust": "none", "format": "csv"})
        status = "target_close_available" if exact_close(body, target) else "target_close_unavailable"
        return {**report, "status": status}
    except HTTPError as error:
        return {**report, "status": "unavailable", "http_status": error.code}
    except (ValueError, OSError, KeyError, TypeError, InvalidOperation):
        return {**report, "status": "response_unverified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=date.fromisoformat)
    print(json.dumps(audit(parser.parse_args().session, os.getenv("FINZDATA_API_KEY", "").strip())))
