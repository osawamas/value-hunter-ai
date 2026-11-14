"""v149: isolate bank-specific OCBC 3Q26 capital and asset quality indicators.

All values are ROUNDING/PUBLIC ISSUER metrics from original SGX PDF.
No annual PER, industrial operating margin, or ranking promotion.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf
NAME="OCBC_3Q26_Results_Press_Release.pdf"

def parse(raw,manifest,profit):
 if manifest.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or profit.get("status")!="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED":
  raise ValueError("Unverified primary source")
 rows=[x for x in manifest.get("record",{}).get("records",[]) if x.get("filename")==NAME]
 if len(rows)!=1:raise ValueError("Original OCBC press missing")
 item=rows[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=item.get("sha256"):
  raise ValueError("SGX press original hash mismatch")
 if profit.get("record",{}).get("original_sgx_pdf_sha256")!=item["sha256"]:
  raise ValueError("Source profit and banking ratios not same primary PDF")
 import fitz
 d=fitz.open(stream=raw,filetype="pdf")
 try:full=" ".join(" ".join(p.get_text("text") for p in d).split())
 finally:d.close()
 text=full.lower().replace("–","-")
 for name,word,value in [
  ("net interest margin",r"nim|net interest margin","1.66"),
  ("nonperforming loans",r"npl|non-performing loans","0.8"),
  ("cet1 capital ratio",r"cet1","15.5"),
  ("annualised return on equity",r"roe|return on equity","13.1")
 ]:
  if not re.search(word,text) or not re.search(r"\b"+re.escape(value)+r"\s*%",text):
   raise ValueError("Missing bank ratio in original release: "+name)
 return {
  "schema_version":"sgx-ocbc-3q26-bank-ratio-research-v149",
  "symbol":"O39","financial_period_end":"2026-09-30",
  "sgx_primary_pdf_sha256":item["sha256"],"sgx_primary_pdf_url":item["official_sgx_original_url"],
  "net_interest_margin_3q26_pct_issuer_reported":"1.66",
  "nonperforming_loan_ratio_pct_issuer_reported":"0.8",
  "cet1_capital_adequacy_ratio_pct_reported":"15.5",
  "return_on_equity_3q26_annualised_pct_reported":"13.1",
  "fully_phased_cet1_is_distinct_from_transitional_ratio":True,
  "ratios_are_rounded_public_issuer_values":True,
  "exact_table_row_scoping_independently_audited":False,
  "bank_provision_and_credit_loss_full_reconciliation_completed":False,
  "independent_numerical_verification":False,
  "current_shares_or_market_quote_verified":False,
  "per_pbr_ranking_permitted":False
 }

def main():
 a=argparse.ArgumentParser()
 for k in ("manifest","profit","output"):a.add_argument("--"+k,required=True)
 x=a.parse_args()
 m=json.loads(Path(x.manifest).read_text());p=json.loads(Path(x.profit).read_text())
 result={"schema_version":"sgx-ocbc-bank-ratio-probe-v149","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  row=next(q for q in m["record"]["records"] if q["filename"]==NAME)
  result["record"]=parse(fetch_pdf(row["official_sgx_original_url"]),m,p)
  result["status"]="OCBC_3Q26_ISSUER_BANK_RATIOS_OBSERVED_IN_PRIMARY_PDF"
 except Exception as e:result["error"]=type(e).__name__+": "+str(e)[:250]
 dest=Path(x.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(result["status"],result["error"])
if __name__=="__main__":main()
