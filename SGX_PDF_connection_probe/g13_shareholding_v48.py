"""G13 as-of 30 June 2026 official issuer share count and treasury movement.

Fail-closed on missing scope/date, inconsistent arithmetic, or PDF regression.
Same-issuer evidence is not independent third-party financial verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://links.sgx.com/FileOpen/2.%20GENS%201H2026%20SGX%20Results%20Announcement.ashx?App=Announcement&FileID=900902"
AS_OF = "2026-06-30"
EXPECTED = {"issued_shares_including_treasury": 12094026824,
            "treasury_shares": 30384550,
            "shares_outstanding": 12063642274,
            "opening_treasury": 8121350,
            "treasury_reissued": 7567000,
            "repurchased": 29830200}


def fetch(timeout=60):
    req = urllib.request.Request(SOURCE, headers={
        "User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI issuer financial research)",
        "Accept":"application/pdf",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw=response.read(15_000_001)
    if len(raw)>15_000_000 or not raw.startswith(b"%PDF"):
        raise ValueError("Missing valid size-limited G13 PDF")
    return raw


def extract_number(pattern,text,field):
    m=re.findall(pattern,text,re.I)
    if len(m)!=1:
        raise ValueError(f"G13 {field} missing/ambiguous: {len(m)}")
    return int(m[0].replace(",",""))


def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        evidence=[]
        for i,page in enumerate(doc):
            t=" ".join(page.get_text("text").split()).replace("’", "'")
            if "SHARE CAPITAL AND TREASURY SHARES" in t and (
                    "As at 30 June 2026, the number of ordinary shares in issue" in t or
                    "The movement in the Company's treasury shares" in t):
                evidence.append((i+1,t))
        if len(evidence)!=2:
            raise ValueError("Missing or duplicated dated share-capital pages")
        summary=next((t for p,t in evidence if "number of ordinary shares in issue was" in t),None)
        movement=next((t for p,t in evidence if "movement in the Company" in t),None)
        if summary is None or movement is None:
            raise ValueError("Official share and treasury movement notes absent")
        regex=r"As at 30 June 2026, the number of ordinary shares in issue was\s+([0-9,]+)\s+of which\s+([0-9,]+)\s+were held by the Company as treasury shares"
        pairs=re.findall(regex,summary,re.I)
        if len(pairs)!=1:
            raise ValueError("Missing exact 30 Jun 2026 gross and treasury figures")
        gross,treasury=(int(s.replace(",","")) for s in pairs[0])
        net=extract_number(r"As at 30 June 2026, total number of issued shares\s*\(excluding treasury shares\) was\s+([0-9,]+)",summary,"net shares")
        opening=extract_number(r"As at 1 January 2026\s+([0-9,]+)",movement,"opening treasury")
        reissued=extract_number(r"Employees of a subsidiary of the Company\s*\(([0-9,]+)\)",movement,"last treasury reissued tranche")
        # Three share transfers: directors 500,000, Company employees 1,171,444,
        # subsidiary employees 5,895,556. Treat the sum as the movement.
        directors=extract_number(r"Independent Non-Executive Directors of the Company\s*\(([0-9,]+)\)",movement,"treasury directors")
        employees=extract_number(r"Employees of the Company\s*\(([0-9,]+)\)",movement,"treasury employees")
        repurchased=extract_number(r"Repurchase of shares\s+([0-9,]+)",movement,"treasury repurchase")
        reissued_total=directors+employees+reissued
        actual={"issued_shares_including_treasury":gross,
                "treasury_shares":treasury,"shares_outstanding":net,
                "opening_treasury":opening,"treasury_reissued":reissued_total,
                "repurchased":repurchased}
        if actual!=EXPECTED:
            raise ValueError(f"G13 official PDF regression changed: {actual}")
        if gross-treasury!=net or opening-reissued_total+repurchased!=treasury:
            raise ValueError("Gross/net and treasury rollforward do not reconcile")
        return {"issued_shares_including_treasury":gross,
                "treasury_shares":treasury,"shares_outstanding":net,
                "share_count_basis":"issued_excluding_treasury",
                "as_of_date":AS_OF,
                "financial_period_end":AS_OF,
                "pdf_pages":[p for p,_ in evidence],
                "treasury_rollforward":{"opening":opening,
                    "shares_reissued":reissued_total,
                    "repurchased":repurchased,
                    "closing":treasury}}
    finally:
        doc.close()


def run(output,raw=None):
    result={"symbol":"G13","status":"NOT_VERIFIED","source_url":SOURCE,
            "pdf_sha256":None,"snapshot":None,"error":None,
            "independent_verification":False}
    try:
        data=fetch() if raw is None else raw
        result["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        result["snapshot"]=parse_pdf(data)
        result["status"]="OFFICIAL_1H2026_GROSS_TREASURY_NET_RECONCILED"
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    ap.add_argument("--offline-pdf")
    args=ap.parse_args()
    r=run(args.output,Path(args.offline_pdf).read_bytes() if args.offline_pdf else None)
    print(r["status"],r["error"])
    raise SystemExit(0 if r["status"]=="OFFICIAL_1H2026_GROSS_TREASURY_NET_RECONCILED" else 1)
