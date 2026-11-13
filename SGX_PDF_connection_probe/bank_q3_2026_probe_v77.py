"""v77: period-aware issuer 3Q26 sources, diagnostic PDF excerpts only.

No silent promotion of numbers from quarterly trading updates. The three
issuers publish trading-updates rather than uniform audited statements.
The period must be explicitly tagged as Q3 or first nine months (9M).
"""
import argparse,hashlib,json,re
from pathlib import Path
from official_http_v57 import get_pdf

SOURCES={
 "D05":{"issuer":"DBS Group Holdings Ltd","url":"https://links.sgx.com/FileOpen/3Q26_trading_update.ashx?App=Announcement&FileID=910439",
        "identity":("DBS","3Q26"),"released":"2026-11-05"},
 "O39":{"issuer":"Oversea-Chinese Banking Corporation Limited",
        "url":"https://links.sgx.com/FileOpen/OCBC_3Q26_Results_Press_Release.ashx?App=Announcement&FileID=910569",
        "identity":("OCBC","2026"),"released":"2026-11-06"},
 "U11":{"issuer":"United Overseas Bank Limited",
        "url":"https://www.uobgroup.com/investor-relations/assets/pdfs/investor/financial/2026/cfo-slides-3q-2026.pdf",
        "identity":("UOB","2026"),"released":"2026-11-04"},
}
CUES=("total income","net interest income","net profit","group net profit",
      "profit attributable","financial performance","nine months",
      "9m26","3q26","3rd qtr 2026","third quarter 2026",
      "total assets","shareholders' funds","earnings","equity holders")

def inspect(symbol,raw):
 import fitz
 if symbol not in SOURCES:raise ValueError("Unsupported 3Q26 issuer")
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
  raise ValueError("3Q26 document does not start with PDF header")
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if not 1<=len(doc)<=200:raise ValueError("Unexpected PDF page count")
  samples=[]
  for i,page in enumerate(doc):
   lines=page.get_text("text").splitlines()
   norm=" ".join(lines).lower()
   terms=[x for x in CUES if x in norm]
   if not terms:continue
   # Save only a small number of evidence snippets, never a numerical claim.
   matches=[]
   for k,line in enumerate(lines):
    if any(x in line.lower() for x in terms):
     matches.append(" | ".join(lines[max(0,k-2):min(len(lines),k+8)])[:520])
   samples.append({"pdf_page_number":i+1,"cues":terms,"nearby_rows":matches[:8]})
  if not samples:raise ValueError("No bank results rows discoverable")
  head=" ".join(doc[i].get_text("text") for i in range(min(4,len(doc)))).lower()
  issuer_tag=SOURCES[symbol]["identity"][0].lower()
  if issuer_tag not in head:raise ValueError("Issuer identity absent from leading pages")
  if not ("2026" in head or any("2026" in " ".join(s["nearby_rows"]) for s in samples)):
   raise ValueError("2026 reporting period not found")
  return {"symbol":symbol,"issuer":SOURCES[symbol]["issuer"],
   "status":"SOURCE_PDF_DIAGNOSTIC_ONLY","financial_period_end":"2026-09-30",
   "released_at_date":SOURCES[symbol]["released"],
   "data_not_extracted":True,
   "q3_definition":"2026-07-01_to_2026-09-30",
   "nine_month_definition":"2026-01-01_to_2026-09-30",
   "warning":"NEVER_MIX_QUARTER_NINEMONTH_AND_ANNUAL",
   "pages":samples[:20],"ranking_eligible":False}
 finally:doc.close()

def run(symbol,output,raw=None):
 source=SOURCES[symbol]
 record={"symbol":symbol,"status":"NOT_VERIFIED","source_url":source["url"],
         "pdf_sha256":None,"evidence":None,"error":None}
 try:
  data=get_pdf(source["url"],max_bytes=75_000_000,timeout=90) if raw is None else raw
  record["pdf_sha256"]=hashlib.sha256(data).hexdigest()
  record["evidence"]=inspect(symbol,data)
  record["status"]="SOURCE_PDF_DIAGNOSTIC_ONLY"
 except Exception as exc:
  record["error"]=f"{type(exc).__name__}: {str(exc)[:280]}"
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return record

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--symbol",choices=tuple(SOURCES),required=True)
 p.add_argument("--output",required=True);p.add_argument("--offline-pdf")
 a=p.parse_args()
 record=run(a.symbol,a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
 print(a.symbol,record["status"],record["error"])
 for page in (record.get("evidence") or {}).get("pages",[])[:12]:
  print(json.dumps(page,ensure_ascii=False)[:3000])
 # Diagnostic fetch denial should remain visible in an Actions status.
 raise SystemExit(0 if record["status"]=="SOURCE_PDF_DIAGNOSTIC_ONLY" else 1)
