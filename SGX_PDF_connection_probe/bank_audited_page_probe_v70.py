"""Diagnostic-only extraction for OCBC/UOB FY2025 audited Group statements.

No numeric values promoted. Print selected page text exactly as extracted to
allow designing strict page/row/scope-aware parsers. Only issuer PDF source.
"""
import argparse, json
from pathlib import Path
from official_http_v57 import get_pdf
from bank_statements_probe_v66 import SOURCES

PAGES={"O39":[124,125,126,127,128],"U11":[136,137,138,139,140]}

def inspect(symbol,raw):
    import fitz
    pdf=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(pdf)<max(PAGES[symbol]):raise ValueError("PDF unexpectedly short")
        info={}
        for page_number in PAGES[symbol]:
            lines=pdf[page_number-1].get_text("text").splitlines()
            info[page_number]=lines[:190]
        return {"symbol":symbol,"status":"DIAGNOSTIC_ONLY",
                "promotion_allowed":False,"pages":info}
    finally: pdf.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",choices=list(PAGES),required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result={"symbol":a.symbol,"status":"NOT_VERIFIED","promotion_allowed":False}
    try:
        raw=get_pdf(SOURCES[a.symbol]["url"],max_bytes=75_000_000,timeout=90)
        result=inspect(a.symbol,raw)
    except Exception as exc:result["error"]=f"{type(exc).__name__}: {str(exc)[:230]}"
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for pg,lines in result.get("pages",{}).items():
        print("===== "+a.symbol+" official PDF page "+str(pg)+" =====")
        print(" | ".join(lines)[:11500])
    if result.get("error"):print(result["error"])
