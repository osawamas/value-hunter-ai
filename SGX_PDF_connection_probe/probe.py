"""S68 PDF connection and verified-financial regression probe.

Outputs are always saved to results/; process exits nonzero unless FY2026
income statement values can be validated from the actual results PDF.
"""
import datetime
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

import pymupdf
from financial_extract import extract_s68_fy2026

URLS = {
    "S68_FY2026_results": "https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584",
    "S68_FY2026_release": "https://links.sgx.com/FileOpen/1.%20SGX%20Group%20reports%20FY2026%20net%20profit%20of%20S%24759%20million.ashx?App=Announcement&FileID=898861",
}
OUT = pathlib.Path("results")
OUT.mkdir(exist_ok=True)
MAX_BYTES = 20_000_000


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ValueHunterFinancialProbe/1.0)",
        "Accept": "application/pdf,*/*;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=35) as response:
        raw = response.read(MAX_BYTES + 1)
        status = response.status
        mime = response.headers.get("Content-Type", "")
    if len(raw) > MAX_BYTES:
        raise ValueError("PDF exceeds 20MB cap")
    if not raw.startswith(b"%PDF-"):
        raise ValueError("response is not a PDF")
    return raw, status, mime


def main():
    report = []
    verified = False
    for name, url in URLS.items():
        record = {
            "name": name, "url": url,
            "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        try:
            data, status, mime = fetch(url)
            doc = pymupdf.open(stream=data, filetype="pdf")
            pages = [page.get_text(sort=True) for page in doc]
            record.update({
                "http_status": status, "content_type": mime,
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "pages": len(pages), "extracted_chars": sum(map(len, pages)),
                "pdf_extraction": "passed",
            })
            if name == "S68_FY2026_results":
                try:
                    result = extract_s68_fy2026(pages)
                    result["document_sha256"] = record["sha256"]
                    result["document_url"] = url
                    (OUT / "S68_verified_financials.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    record["financial_validation"] = "passed"
                    verified = True
                except ValueError as exc:
                    record["financial_validation"] = "not_verified"
                    record["validation_error"] = str(exc)
        except Exception as exc:
            record["pdf_extraction"] = "failed"
            record["error"] = str(exc)
        report.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    (OUT / "report.json").write_text(
        json.dumps({"success": verified, "records": report}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not verified:
        print("FAIL: S68 official FY2026 statement not verified. See results/report.json", file=sys.stderr)
        return 1
    print("PASS: S68 official FY2026 income-statement regression verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
