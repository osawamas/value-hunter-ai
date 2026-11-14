"""v152: exact SGX original OCBC 3Q/9M 2026 profit in SGD millions.

Reads specific labeled PDF table rows, not unrelated prose. Distinguishes
issuer-reported exact-million figures from audited FY2025, independent
third-party verification, current market quotes, and trading valuations.
"""
import argparse,hashlib,json,re
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

NAME="OCBC_3Q26_Results_Press_Release.pdf"
ROWS=(
 ("3Q26",1,"2,042","1,978"),
 ("9M26",3,"6,237","5,677"),
)
def parse_text_lines(lines,label,current,comparison):
 hits=[i for i,line in enumerate(lines) if line.strip()=="Group net profit"]
 if len(hits)!=1:raise ValueError(label+" unique Group net profit table row missing")
 i=hits[0]
 if i+2>=len(lines) or lines[i+1].strip()!=current or lines[i+2].strip()!=comparison:
  raise ValueError(label+" current or comparison profit shifted/modified")
 return {"current_sgd_millions":int(current.replace(",","")),
         "comparison_sgd_millions":int(comparison.replace(",","")),
         "source_table_line":i+1}
def extract(pdf,source,rounded):
 if (source.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or
     rounded.get("status")!="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED"):
  raise ValueError("Underlying original proof not verified")
 rows=[r for r in source.get("record",{}).get("records",[]) if r.get("filename")==NAME]
 if len(rows)!=1:raise ValueError("OCBC original press release PDF ambiguous")
 row=rows[0]
 if not isinstance(pdf,bytes) or not pdf.startswith(b"%PDF") or hashlib.sha256(pdf).hexdigest()!=row["sha256"]:
  raise ValueError("Original source hash mismatch")
 prev=rounded.get("record",{})
 if prev.get("original_sgx_pdf_sha256")!=row["sha256"] or prev.get("period_end_date")!="2026-09-30":
  raise ValueError("Rounded historical source is not same PDF")
 import fitz
 d=fitz.open(stream=pdf,filetype="pdf")
 try:
  if len(d)!=row["page_count"]:raise ValueError("Page count mismatch")
  outputs=[]
  for period,page_i,current,comparison in ROWS:
   page=d[page_i]
   lines=[" ".join(s.split()) for s in page.get_text("text").splitlines() if s.strip()]
   check=" ".join(lines)
   if period not in check:raise ValueError("Financial period missing on expected PDF page")
   parsed=parse_text_lines(lines,period,current,comparison)
   parsed["period"]=period;parsed["pdf_page"]=page_i+1
   parsed["unit"]="SGD_millions"
   outputs.append(parsed)
 finally:d.close()
 q3=Decimal(outputs[0]["current_sgd_millions"])/Decimal(1000)
 nine=Decimal(outputs[1]["current_sgd_millions"])/Decimal(1000)
 if (str(q3.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))!=prev.get("group_net_profit_3q26_sgd_billion_reported") or
     str(nine.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))!=prev.get("group_net_profit_9m26_sgd_billion_reported")):
  raise ValueError("Exact PDF table amounts do not reconcile to previously published rounded press statement")
 return {
  "schema_version":"sgx-ocbc-q3-exact-bank-profit-v152",
  "symbol":"O39","period_end_date":"2026-09-30",
  "official_press_pdf_url":row["official_sgx_original_url"],
  "official_press_sha256":row["sha256"],
  "exact_statement_profit_rows":outputs,
  "rounded_3q26_profit_sgd_billions":str(q3.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),
  "rounded_9m26_profit_sgd_billions":str(nine.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),
  "group_profit_3q26_sgd_millions":outputs[0]["current_sgd_millions"],
  "group_profit_9m26_sgd_millions":outputs[1]["current_sgd_millions"],
  "same_issuer_rounded_summary_arithmetic_reconciled":True,
  "independent_third_party_profit_verification":False,
  "fy2025_audit_opinion_applies_to_2026_q3":False,
  "current_quote_or_shares_verified":False,
  "annual_per_or_pbr_promoted":False,
  "ranking_eligible":False}

def main():
 a=argparse.ArgumentParser()
 for key in ("originals","rounded","output"):a.add_argument("--"+key,required=True)
 p=a.parse_args()
 d=json.loads(Path(p.originals).read_text());q=json.loads(Path(p.rounded).read_text())
 out={"schema_version":"sgx-ocbc-precise-bank-profit-probe-v152",
      "status":"NOT_VERIFIED","record":None,"error":None}
 try:
  orig=next(x for x in d["record"]["records"] if x["filename"]==NAME)
  out["record"]=extract(fetch_pdf(orig["official_sgx_original_url"]),d,q)
  out["status"]="OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:270]
 path=Path(p.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
