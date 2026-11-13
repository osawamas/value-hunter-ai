"""Diagnostic-only S68 FY2026 parent equity locator.

Read the primary consolidated balance sheet from the audited issuer report.
Never publish a parent-equity value until scope, NCI and balance arithmetic
are validated.
"""
import argparse
import json
from pathlib import Path
from s68_official_pdf_v44 import download

KEYS = ("equity attributable", "non-controlling", "non controlling",
        "owners of the company", "equity holders of the company",
        "total equity", "statement of financial position")

def probe(pdf_bytes):
    import fitz
    doc = fitz.open(stream=pdf_bytes,filetype="pdf")
    output=[]
    try:
        for i,p in enumerate(doc):
            txt=p.get_text("text")
            lower=" ".join(txt.lower().split())
            matched=[x for x in KEYS if x in lower]
            if not matched:
                continue
            # First pages are financial results; don't copy entire annual statements
            lines=txt.splitlines()
            samples=[]
            for k,line in enumerate(lines):
                if any(x in line.lower() for x in KEYS):
                    samples.append({"row":k,"context":" | ".join(lines[max(0,k-3):min(len(lines),k+9)])[:650]})
            output.append({"page_pdf_number":i+1,"matched":matched,"contexts":samples[:12]})
        return {"candidate_pages":output[:25],"pages_with_matches":len(output)}
    finally:
        doc.close()

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);args=p.parse_args()
    report={"symbol":"S68","status":"DIAGNOSTIC_ONLY","source_url":None,
            "parent_equity_promoted":False}
    from s68_official_pdf_v44 import SOURCE
    report["source_url"]=SOURCE
    try:
        report.update(probe(download()))
    except Exception as exc:
        report["error"]=f"{type(exc).__name__}: {str(exc)[:260]}"
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False)[:14000])

if __name__=="__main__":main()
