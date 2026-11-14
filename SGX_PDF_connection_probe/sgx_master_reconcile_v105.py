"""v105: fail-closed reconciliation of third-party SGX candidates vs independently acquired official master.

No official SGX master was available to this run. A verified SGX input must be
provided separately; third-party candidates never self-certify as official.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from datetime import date

SYMBOL = re.compile(r"^[A-Z0-9]{1,6}$")
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
OFFICIAL_URL = "https://www.sgx.com/securities/securities-prices?code=stocks"
BOARDS = {"Mainboard", "Catalist", "Global Listing Board"}
FIELDS = {"trading_code", "isin", "trading_name", "market_board", "security_type"}

def load_candidates(doc):
    if (not isinstance(doc, dict) or doc.get("schema_version") !=
        "sgx-third-party-company-candidates-v99" or
        doc.get("coverage") != "PARTIAL_UNVERIFIED" or
        doc.get("full_sgx_listing_completeness_verified") is not False or
        doc.get("eligible_for_ranking") is not False):
        raise ValueError("Untrusted candidate inventory envelope")
    items = doc.get("candidates")
    if not isinstance(items, list) or len(items) < 20 or len(items) > 1200:
        raise ValueError("Invalid candidates")
    symbols = []
    for row in items:
        if (not isinstance(row, dict) or not SYMBOL.fullmatch(row.get("symbol", "")) or
            row.get("financial_verification") is not False or
            row.get("ranking_eligible") is not False):
            raise ValueError("Candidate verification guard")
        symbols.append(row["symbol"])
    if len(set(symbols)) != len(symbols):
        raise ValueError("Duplicate candidate")
    return set(symbols)

def reconcile(candidates, master_csv=None, provenance=None):
    syms = load_candidates(candidates)
    base = {
        "schema_version": "sgx-official-master-reconciliation-v105",
        "candidate_source_sha256": candidates.get("source_json_sha256"),
        "candidate_count": len(syms),
        "candidate_source_type": "THIRD_PARTY_UNVERIFIED",
        "official_master_status": "NOT_AVAILABLE",
        "official_listing_count": None,
        "official_confirmed_candidate_count": 0,
        "candidate_symbols_without_official_match": sorted(syms),
        "official_symbols_outside_candidate_index": [],
        "official_matches": [],
        "official_primary_source_identity_checked": False,
        "official_master_completeness_verified": False,
        "latest_financial_feed_modified": False,
        "ranking_eligible": False,
    }
    if master_csv is None:
        if provenance is not None:
            raise ValueError("Provenance supplied without official raw bytes")
        return base
    if not isinstance(master_csv, bytes) or not (100 <= len(master_csv) <= 4_000_000):
        raise ValueError("Invalid official master bytes")
    if not isinstance(provenance, dict) or set(provenance) != {
        "source_url", "retrieved_utc", "sha256", "document_date", "capture_method",
        "exchange_origin_verified"}:
        raise ValueError("Complete exchange provenance required")
    if (provenance["source_url"] != OFFICIAL_URL or
        provenance["sha256"] != hashlib.sha256(master_csv).hexdigest() or
        provenance["capture_method"] != "DIRECT_SGX_DOWNLOAD" or
        provenance["exchange_origin_verified"] is not True):
        raise ValueError("Exchange master provenance not verified")
    # Guard against fabricated or stale 'official' files. Proof of a direct
    # download is an external operational prerequisite, not a CSV assertion.
    try:
        date.fromisoformat(provenance["document_date"])
        from datetime import datetime, timezone, timedelta
        t = datetime.fromisoformat(provenance["retrieved_utc"])
        if t.tzinfo is None or t > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Invalid retrieval time")
        if abs((t.date() - date.fromisoformat(provenance["document_date"])).days) > 7:
            raise ValueError("Document date not near retrieval")
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid official master date provenance") from exc
    reader = csv.DictReader(io.StringIO(master_csv.decode("utf-8-sig")))
    if not reader.fieldnames or set(reader.fieldnames) != FIELDS:
        raise ValueError("Official CSV schema not recognized")
    master = {}
    for row in reader:
        ticker = row["trading_code"].strip().upper()
        isin = row["isin"].strip().upper()
        name = row["trading_name"].strip()
        board = row["market_board"].strip()
        kind = row["security_type"].strip()
        if (not SYMBOL.fullmatch(ticker) or not ISIN.fullmatch(isin) or
            not name or board not in BOARDS or not kind):
            raise ValueError("Malformed official listing record")
        if ticker in master:
            raise ValueError("Ambiguous duplicate trading counter")
        master[ticker] = {"symbol":ticker,"isin":isin,"name":name,
                          "market_board":board,"security_type":kind}
    if not master or len(master) > 10000:
        raise ValueError("Empty or excessively large official listing")
    overlap = syms & set(master)
    base.update({
        "official_master_status": "INPUT_SCHEMA_AND_PROVENANCE_CHECKED_NOT_INDEPENDENTLY_CERTIFIED",
        "official_listing_count": len(master),
        "official_confirmed_candidate_count": len(overlap),
        "candidate_symbols_without_official_match": sorted(syms - set(master)),
        "official_symbols_outside_candidate_index": sorted(set(master) - syms),
        "official_matches": [master[s] for s in sorted(overlap)],
        "official_primary_source_identity_checked": True,
        # The download may cover only filtered stocks; don't infer completeness.
        "official_master_completeness_verified": False,
        "official_csv_sha256": provenance["sha256"],
        "official_document_date": provenance["document_date"],
    })
    return base

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidates",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--official-csv")
    p.add_argument("--provenance")
    a=p.parse_args()
    candidates=json.loads(Path(a.candidates).read_text(encoding="utf-8"))
    if bool(a.official_csv) != bool(a.provenance):
        p.error("Official CSV and provenance must be supplied together")
    raw=Path(a.official_csv).read_bytes() if a.official_csv else None
    origin=json.loads(Path(a.provenance).read_text()) if a.provenance else None
    result=reconcile(candidates,raw,origin)
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(result["official_master_status"],result["candidate_count"],
          result["official_confirmed_candidate_count"])

if __name__=="__main__":
    main()
