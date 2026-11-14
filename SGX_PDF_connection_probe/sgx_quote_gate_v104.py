"""v104: fail-closed exchange quote identity and timestamp validation.

Research-only gate for future adapters. Strict source/identity/timestamp
checks do not certify an independent market quote or permit valuation.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SGT = ZoneInfo("Asia/Singapore")
SECURITIES = {
    "D05": {"isin": "SG1L01001701", "issuer": "DBS GROUP HOLDINGS LTD"},
    "O39": {"isin": "SG1S04926220", "issuer": "OVERSEA-CHINESE BANKING CORP"},
    "U11": {"isin": "SG1M31001969", "issuer": "UNITED OVERSEAS BANK LTD"},
}
CANDIDATE_SOURCE = "SGX_OFFICIAL_WEB_PAGE_RESEARCH"
FIELDS = ("symbol", "isin", "currency", "exchange", "price", "as_of",
          "source_url", "source_kind")

def validate_quote(item, now=None, max_age_hours=72):
    if not isinstance(item, dict):
        raise ValueError("Quote must be a JSON object")
    if set(item) != set(FIELDS):
        raise ValueError("Exact input schema required")
    symbol = item["symbol"]
    if not isinstance(symbol, str) or symbol not in SECURITIES:
        raise ValueError("Unknown symbol")
    if item["isin"] != SECURITIES[symbol]["isin"]:
        raise ValueError("ISIN mismatch")
    if item["currency"] != "SGD" or item["exchange"] != "XSES":
        raise ValueError("Currency or exchange mismatch")
    if item["source_kind"] != CANDIDATE_SOURCE:
        raise ValueError("Source type not admissible")
    if item["source_url"] != "https://www.sgx.com/securities/securities-prices?code=stocks":
        raise ValueError("Original SGX quote page URL not pinned")
    price = item["price"]
    if type(price) not in (int, float) or not math.isfinite(price) or not 0 < price <= 10000:
        raise ValueError("Price must be positive finite SGD")
    clock = item["as_of"]
    if not isinstance(clock, str):
        raise ValueError("Missing datetime string")
    try:
        observed = datetime.fromisoformat(clock)
    except ValueError as e:
        raise ValueError("Invalid quote datetime") from e
    if observed.tzinfo is None or observed.utcoffset() != timedelta(hours=8):
        raise ValueError("Quote must include explicit SGT +08:00")
    if observed.second != 0 or observed.microsecond != 0:
        raise ValueError("Quote timestamp needs minute precision")
    ref = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(ref, datetime) or ref.tzinfo is None:
        raise ValueError("Reference time must be aware")
    elapsed = ref.astimezone(timezone.utc) - observed.astimezone(timezone.utc)
    if elapsed < timedelta(0) or elapsed > timedelta(hours=max_age_hours):
        raise ValueError("Future or stale timestamp")
    if observed.astimezone(SGT).hour not in range(9, 18):
        raise ValueError("SGX trade timestamp outside conservative day session")
    return {
        "symbol": symbol,
        "isin": item["isin"],
        "price_sgd_research": price,
        "timestamp_sgt": observed.isoformat(timespec="minutes"),
        "source_url": item["source_url"],
        "source_kind": CANDIDATE_SOURCE,
        "identity_and_timestamp_checked": True,
        "independently_corroborated": False,
        "actual_quote_from_sgx_verified": False,
        "eligible_for_market_cap": False,
        "eligible_for_per_pbr": False,
        "eligible_for_ranking": False,
    }

def run(input_path, output_path):
    raw = Path(input_path).read_bytes()
    doc = json.loads(raw)
    if not isinstance(doc, dict) or set(doc) != {"quotes", "source_retrieved_at"}:
        raise ValueError("Quote research envelope invalid")
    if not isinstance(doc["quotes"], list) or len(doc["quotes"]) > len(SECURITIES):
        raise ValueError("Quote list invalid")
    retrieved = datetime.fromisoformat(doc["source_retrieved_at"])
    if retrieved.tzinfo is None:
        raise ValueError("Retrieval timestamp must have timezone")
    records = [validate_quote(x, now=retrieved) for x in doc["quotes"]]
    symbols = [x["symbol"] for x in records]
    if len(symbols) != len(set(symbols)):
        raise ValueError("Repeated quote ticker")
    result = {
        "schema_version": "sgx-quote-research-gate-v104",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "quote_count": len(records),
        "quote_status": "RESEARCH_ONLY_NOT_INDEPENDENTLY_VERIFIED",
        "feed_promotion_allowed": False,
        "market_cap_or_per_pbr_allowed": False,
        "ranking_allowed": False,
        "records": records,
    }
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True)
    a.add_argument("--output",required=True)
    z=a.parse_args()
    print(run(z.input,z.output)["quote_status"])
