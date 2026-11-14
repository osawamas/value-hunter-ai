"""v158 OCBC original SGX primary bank balance-sheet row reconnaissance.

Report only small relevant row neighborhoods. Not yet a validated capital or
shareholders' equity calculation, and not a current market valuation.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf
NAME="OCBC_3Q26_Results_Press_Release.pdf"
TERMS=re.compile(r"(selected balance sheet|total assets|total liabilities|shareholders|"
                 r"equity|customer loans|loans to customers|customer deposits|deposits of|"
                 r"net loans|gross loans|capital adequacy|common equity)",re.I)
def analyze(raw,manifest):
 if manifest.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED":raise ValueError("Unverified manifest")
 entries=[r for r in manifest.get("record",{}).get("records",[]) if r.get("filename")==NAME]
 if len(entries)!=1:raise ValueError("Press original absent")
 r=entries[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=r["sha256"]:
  raise ValueError("Hash mismatch")
 import fitz
 d=fitz.open(stream=raw,filetype="pdf")
 try:
  neighborhoods=[]
  for page_index in (7,8):
   p=d[page_index]
   lines=[" ".join(t.split()) for t in p.get_text("text").splitlines() if t.strip()]
   for n,line in enumerate(lines):
    if not TERMS.search(line):continue
    neighborhoods.append({"pdf_page":page_index+1,"line":line[:160],
      "before":lines[n-1][:100] if n else "",
      "next":lines[n+1][:100] if n+1<len(lines) else "",
      "next2":lines[n+2][:100] if n+2<len(lines) else ""})
  if len(neighborhoods)>70:neighborhoods=neighborhoods[:70]
 finally:d.close()
 if not neighborhoods:raise ValueError("No bank balance sheet labels found")
 return {"schema_version":"sgx-ocbc-q3-bank-balance-row-discovery-v158",
  "symbol":"O39","source_pdf_sha256":r["sha256"],
  "source_pdf_url":r["official_sgx_original_url"],
  "page_selection":[8,9],"row_neighborhoods":neighborhoods,
  "precise_balance_sheet_independently_verified":False,
  "current_share_price_or_equity_valuation_verified":False,
  "ranking_eligible":False}
def main():
 a=argparse.ArgumentParser()
 for key in ("manifest","output"):a.add_argument("--"+key,required=True)
 arg=a.parse_args();m=json.loads(Path(arg.manifest).read_text())
 out={"schema_version":"sgx-ocbc-balance-discovery-probe-v158","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  p=next(v for v in m["record"]["records"] if v["filename"]==NAME)
  out["record"]=analyze(fetch_pdf(p["official_sgx_original_url"]),m)
  out["status"]="OCBC_PRIMARY_BANK_BALANCE_ROWS_EXTRACTED_RESEARCH_ONLY"
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:260]
 o=Path(arg.output);o.parent.mkdir(parents=True,exist_ok=True)
 o.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
