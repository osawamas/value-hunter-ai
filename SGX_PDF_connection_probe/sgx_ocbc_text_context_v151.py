"""v151: bounded OCBC SGX primary press-release page/row table discovery.

Read real trusted original PDF and extract compact line evidence. No OCR,
no equity/profit fabrication and no promotion of financial data.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

NAME="OCBC_3Q26_Results_Press_Release.pdf"
PAT=re.compile(r"(net profit|profit attributable|credit losses|income statement|financial highlights|"
               r"provision|allowances|total assets|total equity|non.controlling|"
               r"shareholders|common equity|net interest income|non.interest income|"
               r"return on equity)",re.I)

def extract(raw,manifest):
 if manifest.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or manifest.get("record",{}).get("symbol")!="O39":
  raise ValueError("Unverified PDF source")
 records=[r for r in manifest["record"]["records"] if r.get("filename")==NAME]
 if len(records)!=1:raise ValueError("Press release missing")
 r=records[0]
 if (not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or
     hashlib.sha256(raw).hexdigest()!=r["sha256"]):
  raise ValueError("PDF digest mismatch")
 import fitz
 document=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(document)!=r["page_count"]:raise ValueError("Page count mismatch")
  matches=[]
  for number,page in enumerate(document):
   lines=[" ".join(line.split()) for line in page.get_text("text").splitlines() if line.strip()]
   for index,line in enumerate(lines):
    if not PAT.search(line):continue
    matches.append({
     "pdf_page":number+1,
     "matching_line":line[:180],
     "line_before":lines[index-1][:180] if index>0 else "",
     "line_after":lines[index+1][:180] if index+1<len(lines) else "",
     "line_next2":lines[index+2][:180] if index+2<len(lines) else ""
    })
 finally:document.close()
 if not matches:raise ValueError("No eligible text rows in real PDF")
 if len(matches)>160:matches=matches[:160]
 return {"schema_version":"sgx-ocbc-3q26-line-structure-v151",
  "symbol":"O39","period_end_date":"2026-09-30",
  "original_pdf_sha256":r["sha256"],"official_pdf_url":r["official_sgx_original_url"],
  "page_count":r["page_count"],"keyword_context_count":len(matches),
  "line_contexts":matches,
  "extracted_precise_bank_accounting_values_verified":False,
  "any_independent_earnings_recalculation":False,
  "current_price_or_shares_approved":False,
  "ranking_eligible":False}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--manifest",required=True);parser.add_argument("--output",required=True)
 a=parser.parse_args()
 out={"schema_version":"sgx-ocbc-line-structure-probe-v151","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  manifest=json.loads(Path(a.manifest).read_text())
  r=next(x for x in manifest["record"]["records"] if x["filename"]==NAME)
  out["record"]=extract(fetch_pdf(r["official_sgx_original_url"]),manifest)
  out["status"]="SGX_OCBC_ORIGINAL_TEXT_CONTEXTS_EXTRACTED"
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:260]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"],out["record"] and out["record"]["keyword_context_count"])
if __name__=="__main__":main()
