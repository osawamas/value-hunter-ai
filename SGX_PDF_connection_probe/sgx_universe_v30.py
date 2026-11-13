"""SGX issuer registry: source-backed discovery without claiming full SGX coverage.

An issuer is catalogued only when a valid symbol, issuer name and primary
document URL are provided. Registration does not mean verified financials.
"""
import json
import re
from pathlib import Path

SYMBOL = re.compile(r"^[A-Z0-9]{1,8}$")
MAX_ISSUERS = 1500

def validate_universe(catalog):
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "sgx_issuer_universe_v30":
        raise ValueError("Unsupported universe schema")
    issuers = catalog.get("issuers")
    if not isinstance(issuers, list) or not issuers or len(issuers) > MAX_ISSUERS:
        raise ValueError("Invalid universe count")
    seen = set()
    clean = []
    for index, row in enumerate(issuers):
        if not isinstance(row, dict):
            raise ValueError(f"Invalid issuer at {index}")
        symbol = row.get("symbol")
        issuer = row.get("issuer")
        pdf = row.get("financial_pdf_url")
        if not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) or symbol in seen:
            raise ValueError(f"Duplicate/invalid SGX symbol: {symbol!r}")
        if not isinstance(issuer, str) or not 2 <= len(issuer.strip()) <= 200:
            raise ValueError(f"Invalid company name for {symbol}")
        if not isinstance(pdf, str) or not pdf.startswith("https://") or len(pdf) > 2048:
            raise ValueError(f"Missing HTTPS source for {symbol}")
        if row.get("market") != "SGX" or row.get("currency") != "SGD":
            raise ValueError(f"Unexpected market or currency for {symbol}")
        seen.add(symbol)
        clean.append(dict(row))
    return clean

def read_universe(path):
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_universe(catalog)
