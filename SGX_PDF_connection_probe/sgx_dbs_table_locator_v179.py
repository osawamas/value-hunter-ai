"""v179: evidence-bound DBS official SGX 3Q26 trading-update table locator.

Extract bounded contexts only. Finding a number in a page does not independently
prove which accounting column the number belongs to.
"""
import argparse, hashlib, json, re
from pathlib import Path
from sgx_big3_nii_v177 import fetch
from sgx_big3_nii_v177 import URL

LABEL=re.compile(r"^(?:Net interest income|Net fee income|Non-interest income|Total income|Net profit|"
                 r"Profit attributable to shareholders|Profit attributable to equity holders)$",re.I)
HEAD=re.compile(r"(?:3Q26|3Q25|9M26|9M25|third quarter|nine months|2026)",re.I)
def inspect(raw,previous):
 if previous.get("status")!="SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED":
  raise ValueError("Prior original-source validation absent")
 p=previous.get("record",{})
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=p.get("dbs_official_trading_pdf_sha256"):
  raise ValueError("DBS source hash does not match v177 official SGX original")
 if p.get("dbs_trading_pdf_single_table_row_column_reperformance_completed") is not False:
  raise ValueError("Prior source status improperly promoted")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  located=[]
  for page_number,page in enumerate(doc):
   lines=[" ".join(z.split()) for z in page.get_text("text").splitlines() if z.strip()]
   for i,line in enumerate(lines):
    if LABEL.fullmatch(line) or HEAD.search(line) and len(line)<90:
     if not LABEL.fullmatch(line) and not any(x in line for x in ("3Q26","9M26")):
      continue
     located.append({"pdf_page":page_number+1,"label_or_period":line[:120],
       "previous":lines[max(0,i-4):i],"following":lines[i+1:i+16]})
 finally:doc.close()
 if not any("Net interest income" in row["label_or_period"] for row in located):
  raise ValueError("No actual DBS original NII table labels")
 if not any("3Q26" in row["label_or_period"] or "9M26" in row["label_or_period"] for row in located):
  raise ValueError("No exact original period labels")
 if len(located)>120:located=located[:120]
 return {"schema_version":"sgx-dbs-3q26-tabular-row-layout-v179",
  "symbol":"D05","original_trading_pdf_url":URL,
  "original_trading_pdf_sha256":p["dbs_official_trading_pdf_sha256"],
  "period_end":"2026-09-30","source_table_contexts":located,
  "exact_row_column_validation_completed":False,
  "historical_original_only":True,"independent_third_party_audit":False,
  "current_quote_or_treasury_shares_verified":False,"ranking_eligible":False}

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--previous",required=True);a.add_argument("--output",required=True);args=a.parse_args()
 out={"schema_version":"sgx-dbs-3q26-table-context-probe-v179","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  previous=json.loads(Path(args.previous).read_text())
  out["record"]=inspect(fetch(),previous)
  out["status"]="DBS_SGX_PRIMARY_TRADING_TABLE_CONTEXTS_CAPTURED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:250]
 t=Path(args.output);t.parent.mkdir(parents=True,exist_ok=True)
 t.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
