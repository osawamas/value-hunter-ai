"""DBS (D05) FY2025 annual report: dated shareholding evidence only.

The 10 February 2026 shareholding table is HISTORICAL, not a current quote.
Do not promote it to market-cap, PER/PBR or investment ranking eligibility.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from official_http_v57 import get_pdf

SOURCE = "https://www.dbs.com/iwov-resources/images/investors/annual-report/dbs-annual-report-2025.pdf"
AS_OF = "2026-02-10"
EXPECTED_NET = 2837558046
EXPECTED_TREASURY = 113424


def fetch():
    return get_pdf(SOURCE, max_bytes=45_000_000, timeout=75)


def parse_pdf(raw):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("DBS official annual source is not a PDF")
    doc = fitz.open(stream=raw, filetype="pdf")
    try:
        if len(doc) < 50 or "DBS" not in doc[0].get_text("text"):
            raise ValueError("Issuer/year/report identity not established")
        found = []
        for i, page in enumerate(doc):
            text = " ".join(page.get_text("text").split())
            if not ("Shareholding statistics" in text
                    and "10 February 2026" in text
                    and "Total number of issued ordinary shares" in text
                    and "Treasury Shares" in text):
                continue
            net_matches = re.findall(
                r"Total number of issued ordinary shares\s*[–—-]\s*([0-9,]+)\s*\(excluding treasury shares\)",
                text, re.I)
            treasury_matches = re.findall(
                r"Treasury Shares\s*[–—-]\s*([0-9,]+)\s*\(",
                text, re.I)
            if len(net_matches)!=1 or len(treasury_matches)!=1:
                raise ValueError("Missing/ambiguous 2026 dated DBS share count")
            net=int(net_matches[0].replace(",",""))
            treasury=int(treasury_matches[0].replace(",",""))
            if net != EXPECTED_NET or treasury != EXPECTED_TREASURY:
                raise ValueError("DBS report share-count regression mismatch")
            gross=net+treasury
            if gross<=net or treasury<0:
                raise ValueError("DBS share-count arithmetic failed")
            found.append({
                "page_pdf_number":i+1,"as_of_date":AS_OF,
                "shares_outstanding":net,"treasury_shares":treasury,
                "issued_shares_including_treasury_derived":gross,
                "share_count_basis":"issued_excluding_treasury",
                "gross_issued_source_kind":"CALCULATED_NET_PLUS_TREASURY",
                "quote_data_available":False,
                "investment_ranking_eligible":False,
            })
        if len(found)!=1:
            raise ValueError(f"Expected one DBS shareholding page; found {len(found)}")
        return found[0]
    finally:
        doc.close()


def run(output, raw=None):
    record={"symbol":"D05","status":"NOT_VERIFIED",
            "source_url":SOURCE,"pdf_sha256":None,
            "snapshot":None,"error":None}
    try:
        source=fetch() if raw is None else raw
        record["pdf_sha256"]=hashlib.sha256(source).hexdigest()
        record["snapshot"]=parse_pdf(source)
        record["status"]="OFFICIAL_DATED_SHAREHOLDING_NET_TREASURY_RECONCILED"
    except Exception as exc:
        record["error"]=f"{type(exc).__name__}: {str(exc)[:350]}"
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return record


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--output",required=True)
    args.add_argument("--offline-pdf")
    options=args.parse_args()
    result=run(options.output,Path(options.offline_pdf).read_bytes() if options.offline_pdf else None)
    print(result["status"],result["error"])
    raise SystemExit(0 if result["status"]=="OFFICIAL_DATED_SHAREHOLDING_NET_TREASURY_RECONCILED" else 1)
