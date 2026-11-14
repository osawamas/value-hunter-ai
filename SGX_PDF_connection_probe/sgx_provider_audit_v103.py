"""v103: provenance-only live provider audit; never used for valuations."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sgx_companies_api_v98 import FETCH_URL, fetch

CODE = re.compile(r"^[A-Z0-9]{1,6}$")
STATUS_FIELDS = ("is_active", "active", "status", "listing_status", "delisting_date",
                 "delisted_at", "delisted_date", "board", "security_type", "instrument_type")
REQUIRED_FIELDS = ("ticker", "symbol", "stock_code", "company_name", "name")

def inspect(raw):
    source = json.loads(raw.decode("utf-8"))
    if not isinstance(source, dict) or not isinstance(source.get("data"), list):
        raise ValueError("Invalid provider response")
    rows = source["data"]
    if not 20 <= len(rows) <= 1200:
        raise ValueError("Provider row count out of bounds")
    invalid = []
    flags = []
    seen = set()
    available = set()
    counts = {"active_true": 0, "active_false": 0, "active_unknown": 0,
              "delisting_date_present": 0, "explicit_inactive": 0}
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise ValueError("Unexpected non-object provider row")
        available.update(item)
        raw_code = item.get("ticker") or item.get("symbol") or item.get("stock_code")
        raw_name = item.get("company_name") or item.get("name")
        code = raw_code.strip().upper() if isinstance(raw_code, str) else None
        valid = bool(code and CODE.fullmatch(code) and
                     isinstance(raw_name, str) and len(raw_name.strip()) >= 3)
        reasons = []
        if not code or not CODE.fullmatch(code):
            reasons.append("INVALID_OR_MISSING_TICKER")
        if not isinstance(raw_name, str) or len(raw_name.strip()) < 3:
            reasons.append("INVALID_OR_MISSING_NAME")
        if valid and code in seen:
            reasons.append("DUPLICATE_TICKER")
            valid = False
        if valid:
            seen.add(code)
        else:
            # Keep only identifying and classification fields, not private/free-text content.
            safe_keys = REQUIRED_FIELDS + STATUS_FIELDS
            invalid.append({"row_index": index, "reason_codes": reasons,
                            "provider_fields": {k: item[k] for k in safe_keys if k in item}})
            continue
        state = item.get("is_active")
        if type(state) is bool:
            counts["active_true" if state else "active_false"] += 1
        else:
            counts["active_unknown"] += 1
        dates = [k for k in ("delisting_date", "delisted_at", "delisted_date") if item.get(k)]
        if dates:
            counts["delisting_date_present"] += 1
        text_status = str(item.get("listing_status", item.get("status", ""))).lower()
        inactive = state is False or bool(dates) or text_status in ("inactive", "delisted", "delisting")
        if inactive:
            counts["explicit_inactive"] += 1
        if state is False or dates or text_status:
            flags.append({"symbol": code, "provider_is_active": state if type(state) is bool else None,
                          "provider_listing_status": item.get("listing_status", item.get("status")),
                          "provider_delisting_dates": {k: item[k] for k in dates},
                          "third_party_inactive_signal": inactive,
                          "sgx_official_listing_status_verified": False})
    return {
        "schema_version": "sgx-provider-quality-audit-v103",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": FETCH_URL,
        "source_response_sha256": hashlib.sha256(raw).hexdigest(),
        "source_kind": "THIRD_PARTY_NOT_OFFICIAL_SGX_MASTER",
        "provider_total": (source.get("meta") or {}).get("total"),
        "provider_raw_rows": len(rows),
        "accepted_rows": len(seen),
        "rejected_rows": len(invalid),
        "rejected_row_details": invalid,
        "observed_status_fields": sorted(set(STATUS_FIELDS) & available),
        "status_field_counts": counts,
        "provider_status_signals": flags,
        "sgx_master_comparison_completed": False,
        "ranking_eligible": False,
        "promoted_to_financial_feed": False
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = inspect(fetch())
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("v103 provider audit:", result["provider_raw_rows"], "raw,",
          result["accepted_rows"], "accepted,", result["rejected_rows"], "rejected")
    print("Status fields:", result["observed_status_fields"])

if __name__ == "__main__":
    main()
