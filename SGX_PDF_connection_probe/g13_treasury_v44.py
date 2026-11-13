"""Audit G13 treasury-share subtraction from the official FY2025 issuer PDF.

Historic FY2025 figures MUST NOT be promoted to the 2026 share snapshot.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://gentingsingapore.listedcompany.com/newsroom/20260224_173326_G13_A7CVA3KL4JFGECGT.2.pdf"
EXPECTED = {
    "2025": {"issued": 12094026824, "treasury": 8121350, "outstanding": 12085905474},
    "2024": {"issued": 12094026824, "treasury": 21494350, "outstanding": 12072532474},
}


def download(timeout=60):
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(20_000_001)
    if not raw.startswith(b"%PDF") or len(raw) > 20_000_000:
        raise ValueError("Not an accepted PDF")
    return raw


def parse_pdf(raw):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid PDF")
    pdf = fitz.open(stream=raw, filetype="pdf")
    try:
        text = "\n".join(page.get_text("text") for page in pdf)
    finally:
        pdf.close()
    normalized = " ".join(text.split())
    if "Number of Issued Shares excluding Treasury Shares" not in normalized:
        raise ValueError("Missing G13 treasury-excluded share table")
    if "Treasury Shares" not in normalized:
        raise ValueError("Missing treasury disclosure")
    for year, expected in EXPECTED.items():
        if expected["issued"] - expected["treasury"] != expected["outstanding"]:
            raise ValueError("Arithmetic mismatch")
        number = f'{expected["outstanding"]:,}'
        if number not in normalized:
            raise ValueError(f"Missing official excluded-treasury total for {year}")
        treasury_number = f'{expected["treasury"]:,}'
        if treasury_number not in normalized:
            raise ValueError(f"Missing treasury count for {year}")
    if "12,094,026,824" not in normalized:
        raise ValueError("Missing total issued count for treasury reconciliation")
    return {
        year: {**figures, "as_of_date": f"{year}-12-31",
               "share_count_basis": "issued_excluding_treasury",
               "status": "OFFICIAL_FY2025_PDF_ARITHMETIC_MATCHED"}
        for year, figures in EXPECTED.items()
    }


def run(output, raw=None):
    record = {"symbol": "G13", "source_url": SOURCE, "pdf_sha256": None,
              "status": "NOT_VERIFIED", "periods": {}, "error": None,
              "latest_2026_snapshot_treasury_basis_verified": False,
              "note": "FY2025 verification does not establish the treasury basis of the 2026-08-14 IR quote count."}
    try:
        data = download() if raw is None else raw
        record["pdf_sha256"] = hashlib.sha256(data).hexdigest()
        record["periods"] = parse_pdf(data)
        record["status"] = "FY2025_TREASURY_DEDUCTION_ARITHMETIC_MATCHED"
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--offline-pdf")
    a = p.parse_args()
    result = run(a.output, Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(result["status"], result["error"])
    raise SystemExit(0 if result["status"] == "FY2025_TREASURY_DEDUCTION_ARITHMETIC_MATCHED" else 1)
