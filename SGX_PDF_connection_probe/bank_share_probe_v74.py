"""Diagnostic 2026 issuer annual-report shareholding tables (no promotions)."""
import argparse,json
from pathlib import Path
from official_http_v57 import get_pdf
from bank_statements_probe_v66 import SOURCES

def scan(symbol,raw):
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 result=[]
 try:
  for i,page in enumerate(doc):
   lines=page.get_text("text").splitlines()
   text=" ".join(lines).lower()
   if not any(t in text for t in ("statistics of shareholdings","shareholding statistics","treasury shares and subsidiary holdings")):continue
   if "2026" not in text or "treasury share" not in text:continue
   result.append({"pdf_page_number":i+1,"lines":lines[:230]})
  return {"symbol":symbol,"status":"DIAGNOSTIC_ONLY","source_url":SOURCES[symbol]["url"],"pages":result[:8],"promotion_allowed":False}
 finally:doc.close()

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--symbol",choices=["O39","U11"],required=True);p.add_argument("--output",required=True);a=p.parse_args()
 output={"symbol":a.symbol,"status":"NOT_VERIFIED","promotion_allowed":False}
 try:output=scan(a.symbol,get_pdf(SOURCES[a.symbol]["url"],max_bytes=75_000_000,timeout=90))
 except Exception as exc:output["error"]=f"{type(exc).__name__}: {str(exc)[:260]}"
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for row in output.get("pages",[]):
  print("PAGE",a.symbol,row["pdf_page_number"]);print(" | ".join(row["lines"])[:11000])
 print(output.get("error",""))
