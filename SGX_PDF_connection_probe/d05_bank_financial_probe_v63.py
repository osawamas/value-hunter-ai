"""Diagnostic, non-promoting DBS financial-statement row locator."""
import argparse
import json
import re
from pathlib import Path
from d05_shareholding_v62 import fetch

PHRASES=("consolidated income statement","consolidated balance sheet",
"total income","net interest income","shareholders of the parent",
"total assets","total liabilities","total shareholders' funds",
"allowances for credit and other losses")

def inspect(raw):
    import fitz
    pdf=fitz.open(stream=raw,filetype="pdf")
    try:
        matches=[]
        for i,p in enumerate(pdf):
            lines=p.get_text("text").splitlines()
            full=" ".join(lines).lower()
            if not any(z in full for z in PHRASES):
                continue
            if i>230: continue
            cells=[]
            for k,line in enumerate(lines):
                if any(z in line.lower() for z in PHRASES):
                    cells.append({"term":line[:90],"near":" | ".join(lines[max(k-2,0):min(k+9,len(lines))])[:470]})
            if cells and (len(cells)>2 or "consolidated income statement" in full or "consolidated balance sheet" in full):
                matches.append({"pdf_page":i+1,"hits":cells[:11]})
        return matches[:45]
    finally: pdf.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result={"symbol":"D05","status":"DIAGNOSTIC_ONLY","metrics_promoted":False}
    try: result["pages"]=inspect(fetch())
    except Exception as exc:result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for entry in result.get("pages",[]):
        print(json.dumps(entry,ensure_ascii=False)[:2500])
    if result.get("error"):print(result["error"])

if __name__=="__main__":main()
