from official_http_v57 import get_pdf
"""S68 annual-report shareholding statistics, exact 1 September 2026.

Derived from official SGX 2026 Annual Report; never treat income-statement
year-end treasury-share values as shareholding-date values.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://links.sgx.com/FileOpen/2026%20SGX%20Annual%20Report.ashx?App=Announcement&FileID=905317"
AS_OF_DATE = "2026-09-01"
EXPECTED = {"issued_shares_including_treasury": 1071642400,
            "treasury_shares": 798916,
            "shares_outstanding": 1070843484}


def fetch(timeout=75):
    return get_pdf(SOURCE,max_bytes=45_000_000,timeout=timeout)


def parse_pdf(data):
    import fitz
    if not isinstance(data, bytes) or not data.startswith(b"%PDF"):
        raise ValueError("Invalid official PDF")
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        candidates = []
        for page_number in range(len(doc)):
            txt = " ".join(doc[page_number].get_text("text").split())
            if "Statistics of Shareholdings" not in txt or "1 September 2026" not in txt:
                continue
            if not all(s in txt for s in (
                "Number of Issued and Paid-up Shares",
                "Number of treasury shares",
                "excluding treasury shares",
            )):
                raise ValueError("Statistics headings absent")
            def row_amount(label):
                pattern = re.compile(re.escape(label) + r"\s*:?\s*([0-9][0-9,]*)", re.I)
                values = [int(x.replace(",", "")) for x in pattern.findall(txt)]
                if len(values) != 1:
                    raise ValueError("Ambiguous/missing "+label)
                return values[0]
            issued = row_amount("Number of Issued and Paid-up Shares")
            treasury = row_amount("Number of treasury shares")
            # The distribution table's total is printed before the subsection
            # on treasury shares. Tie it to the same statistics page and date.
            distribution = txt.split("Treasury shares and subsidiary holdings")[0]
            matches = re.findall(r"\bTotal\s+[0-9,]+\s+100(?:\.00)?\s+([0-9,]+)\s+100(?:\.00)?\b", distribution)
            if len(matches) != 1:
                raise ValueError("Ambiguous distribution net shares total")
            outstanding = int(matches[0].replace(",", ""))
            actual = {"issued_shares_including_treasury": issued,
                      "treasury_shares": treasury,
                      "shares_outstanding": outstanding}
            if actual != EXPECTED or issued - treasury != outstanding:
                raise ValueError("Shareholding regression/equation mismatch")
            candidates.append({**actual, "page_pdf_number": page_number+1,
                               "share_count_basis": "issued_excluding_treasury",
                               "as_of_date": AS_OF_DATE})
        if len(candidates) != 1:
            raise ValueError(f"Expected exactly one shareholding statistics page, found {len(candidates)}")
        return candidates[0]
    finally:
        doc.close()


def run(output, raw=None, verified_pdf_copy=None):
    record = {"symbol": "S68", "source_url": SOURCE,
              "status": "NOT_VERIFIED", "pdf_sha256": None,
              "snapshot": None, "error": None}
    try:
        data = raw if raw is not None else fetch()
        record["pdf_sha256"] = hashlib.sha256(data).hexdigest()
        record["snapshot"] = parse_pdf(data)
        record["status"] = "OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED"
        if verified_pdf_copy is not None:
            target_pdf = Path(verified_pdf_copy)
            target_pdf.parent.mkdir(parents=True, exist_ok=True)
            target_pdf.write_bytes(data)
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {str(exc)[:350]}"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--offline-pdf")
    ap.add_argument("--verified-pdf-copy")
    args = ap.parse_args()
    result = run(args.output, Path(args.offline_pdf).read_bytes() if args.offline_pdf else None, args.verified_pdf_copy)
    print(result["status"], result["error"])
    raise SystemExit(0 if result["status"] == "OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED" else 1)
