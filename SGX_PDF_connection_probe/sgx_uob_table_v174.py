"""v174 probe exact UOB CFO source-page table locations for next row/column verifier."""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_uob_q3_v172 import fetch,PDF
from urllib.request import Request,urlopen
from urllib.parse import urlparse
def source():
 with urlopen(Request(PDF,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI original PDF","Accept":"application/pdf"}),timeout=30) as r:
  u=urlparse(r.geturl())
  if u.scheme!="https" or u.hostname!="links.sgx.com" or not u.path.startswith("/FileOpen/"):
   raise ValueError("SGX origin mismatch")
  return r.read(12_000_001)
def inspect(raw,verified):
 if verified.get("status")!="UOB_Q3_CFO_PRIMARY_SGX_PDF_VERIFIED":raise ValueError("Unverified previous PDF")
 ref=verified["record"]
 if ref.get("symbol")!="U11" or ref.get("financial_period_end")!="2026-09-30" or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=ref["source_pdf_sha256"]:
  raise ValueError("UOB Q3 original digest mismatch")
 import fitz
 d=fitz.open(stream=raw,filetype="pdf")
 try:
  found=[]
  for i,page in enumerate(d):
   lines=[" ".join(x.split()) for x in page.get_text("text").splitlines() if x.strip()]
   for j,line in enumerate(lines):
    if re.search(r"^(?:Net profit|Net interest income|Total income|Net fee income)$|3Q26\s*\(\$m\)|9M26\s*\(\$m\)",line,re.I):
     found.append({"pdf_page":i+1,"row_label":line[:90],
       "before":lines[j-1][:90] if j else "",
       "following":lines[j+1:j+11]})
 finally:d.close()
 if not found:raise ValueError("No finance table labels in 2026 SGX UOB CFO")
 return {"schema_version":"sgx-uob-quarter-financial-row-discovery-v174",
  "symbol":"U11","official_pdf_sha256":ref["source_pdf_sha256"],
  "financial_period_end":"2026-09-30","line_contexts":found[:65],
  "strict_row_column_mapping_done":False,
  "independent_third_party_reperformance":False,
  "current_treasury_shares_or_quote_verified":False,
  "ranking_eligible":False}
def main():
 a=argparse.ArgumentParser();a.add_argument("--source",required=True);a.add_argument("--output",required=True);args=a.parse_args()
 prior=json.loads(Path(args.source).read_text())
 out={"schema_version":"sgx-uob-financial-row-probe-v174","status":"NOT_VERIFIED","record":None,"error":None}
 try:out["record"]=inspect(source(),prior);out["status"]="UOB_PRIMARY_CFO_FINANCIAL_ROW_CONTEXTS_IDENTIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:200]
 p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
 print(out["status"],out["error"])
if __name__=="__main__":main()
