"""v146: extract 3Q2026 OCBC group net profit from SGX original press PDF.

Comparison with OCBC's own public release is SAME ISSUER consistency, not an
independent party review. Bank profit is not industrial operating profit.
"""
import argparse,hashlib,json,re
from decimal import Decimal
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

FILENAME="OCBC_3Q26_Results_Press_Release.pdf"
def parse(raw,pdfs):
 if (not isinstance(pdfs,dict) or pdfs.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or
     pdfs.get("record",{}).get("schema_version")!="sgx-ocbc-q3-pdf-originals-v145"):
  raise ValueError("SGX original PDF not verified")
 matches=[x for x in pdfs["record"].get("records",[]) if x.get("filename")==FILENAME]
 if len(matches)!=1:raise ValueError("Press release PDF missing")
 item=matches[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=item.get("sha256"):
  raise ValueError("Original OCBC press release SHA mismatch")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:text=" ".join(" ".join(p.get_text("text") for p in doc).split())
 finally:doc.close()
 required=[
  r"Third Quarter 2026 Results Press Release",
  r"OCBC Group Third Quarter 2026 Net Profit at S\$2\.04 billion",
  r"Nine-month Group net profit up 10% to a record S\$6\.24 billion",
  r"Group net profit for the third quarter.*?S\$2\.04 billion.*?up 3% year-on-year",
  r"3Q26",r"9M26"
 ]
 for pattern in required:
  if not re.search(pattern,text,re.I):
   raise ValueError("Missing original PDF 3Q26 reported value or scope: "+pattern[:45])
 return {
  "schema_version":"sgx-ocbc-3q26-official-bank-results-v146",
  "symbol":"O39","issuer":"Oversea-Chinese Banking Corporation Limited",
  "period_end_date":"2026-09-30","financial_type":"BANK",
  "group_net_profit_3q26_sgd_billion_reported":"2.04",
  "group_net_profit_9m26_sgd_billion_reported":"6.24",
  "group_net_profit_3q26_yoy_pct_reported":3,
  "group_net_profit_9m26_yoy_pct_reported":10,
  "reported_values_are_rounded_in_original_release":True,
  "original_sgx_press_release_url":item["official_sgx_original_url"],
  "original_sgx_pdf_sha256":item["sha256"],
  "same_issuer_release_values_compared":True,
  "independent_third_party_earnings_verification":False,
  "quarter_is_audited_annual_2025":False,
  "annualised_per_calculated":False,
  "exact_sgx_execution_quote_verified":False,
  "current_treasury_adjusted_shares_verified":False,
  "ranking_eligible":False
 }

def main():
 p=argparse.ArgumentParser();p.add_argument("--pdfs",required=True);p.add_argument("--output",required=True)
 a=p.parse_args();src=json.loads(Path(a.pdfs).read_text())
 out={"schema_version":"sgx-ocbc-q3-metrics-probe-v146","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  item=next(x for x in src["record"]["records"] if x["filename"]==FILENAME)
  out["record"]=parse(fetch_pdf(item["official_sgx_original_url"]),src)
  out["status"]="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:270]
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
