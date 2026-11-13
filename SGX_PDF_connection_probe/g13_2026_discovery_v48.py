"""Discovery-only probe for G13 1H2026 source document.

No values are promoted into valuations. URLs are candidates until an actual
issuer-identified, period-matched PDF is fetched successfully.
"""
import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

CANDIDATES = [
    "https://links.sgx.com/FileOpen/2.%20GENS%201H2026%20SGX%20Results%20Announcement.ashx?App=Announcement&FileID=900902",
    "https://links.sgx.com/FileOpen/2.%20GENS%201H2026%20SGX%20Results%20Announcement.pdf?App=Announcement&FileID=900902",
    "https://links.sgx.com/FileOpen/GENS%201H2026%20SGX%20Results%20Announcement.ashx?App=Announcement&FileID=900902",
]


def probe(url):
    import fitz
    request = urllib.request.Request(url, headers={
        "User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI SGX issuer financial research)",
        "Accept":"application/pdf",
    })
    with urllib.request.urlopen(request, timeout=50) as response:
        data=response.read(12_000_001)
    if not data.startswith(b"%PDF") or len(data)>12_000_000:
        raise ValueError("Not a size-limited PDF")
    doc=fitz.open(stream=data,filetype="pdf")
    try:
        pages=[page.get_text("text") for page in doc]
    finally:
        doc.close()
    joined="\n".join(pages)
    normalized=" ".join(joined.split()).lower()
    if "genting singapore" not in normalized or "30 june 2026" not in normalized:
        raise ValueError("Wrong issuer/financial period")
    match_pages=[]
    for i,text in enumerate(pages):
        if re.search(r"share capital and treasury shares",text,re.I):
            match_pages.append({
                "page_pdf_number":i+1,
                "excerpt":" ".join(text.split())[:5500]
            })
    return {"url":url,"pdf_sha256":hashlib.sha256(data).hexdigest(),
            "pdf_pages":len(pages), "share_capital_pages":match_pages}


def run(output):
    attempts=[]
    record={"symbol":"G13","period_end":"2026-06-30",
            "status":"OFFICIAL_PDF_NOT_YET_IDENTIFIED",
            "candidate_results":[],"share_numbers_promoted":False}
    for url in CANDIDATES:
        try:
            result=probe(url)
            record.update(status="ISSUER_PERIOD_PDF_FOUND_REQUIRES_SHARE_EXTRACTION",
                          candidate_results=[result])
            break
        except Exception as exc:
            attempts.append({"candidate_url":url,
                             "error":f"{type(exc).__name__}: {str(exc)[:280]}"})
    record["attempts"]=attempts
    dest=Path(output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return record


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True)
    args=a.parse_args()
    x=run(args.output)
    print(json.dumps({"status":x["status"],"attempts":x["attempts"],
                      "results":x["candidate_results"]},ensure_ascii=False)[:7500])
