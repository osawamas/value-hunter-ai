"""v154: OCBC 2026Q3 and 9M bank income components from exact SGX PDF tables.

Original issuer data only. All numbers SGD millions; strict page, label, year
and original hash. Avoid classifying bank net interest income as industrial sales.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

NAME="OCBC_3Q26_Results_Press_Release.pdf"
# Values fixed only after v151 real SGX original page-text context discovery.
EXPECTED={
 "3Q26":{"page":2,"net_interest_income":2313,"non_interest_income":1420,
         "operating_profit_before_allowances":2211,"allowances_charged":52},
 "9M26":{"page":4,"net_interest_income":6798,"non_interest_income":4933,
         "operating_profit_before_allowances":7129,"allowances_charged":424}
}
ALIASES={
 "net_interest_income":"Net interest income",
 "non_interest_income":"Non-interest income",
 "operating_profit_before_allowances":"Operating profit before allowances",
 "allowances_charged":"Allowances"
}
def find_table_amount(lines,label,expected):
 hits=[i for i,x in enumerate(lines) if x.strip()==label]
 if len(hits)!=1:raise ValueError("Original unique table line absent: "+label)
 i=hits[0]
 if i+1>=len(lines):raise ValueError("No amount below "+label)
 text=lines[i+1].strip()
 if text!=f"{expected:,}" and not (label=="Allowances" and text==f"({expected:,})"):
  raise ValueError("SGX original row amount mismatch for "+label+": "+text[:40])
 return {"value_sgd_millions":expected,"line":i+1,
         "negative_expense_presentation":text.startswith("(")}
def extract(raw,originals,profit):
 if (originals.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or
     profit.get("status")!="OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED"):
  raise ValueError("Trusted source chain incomplete")
 docs=[x for x in originals.get("record",{}).get("records",[]) if x.get("filename")==NAME]
 if len(docs)!=1:raise ValueError("Original press document missing")
 record=docs[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=record["sha256"]:
  raise ValueError("Original primary PDF digest mismatch")
 if (profit.get("record",{}).get("official_press_sha256")!=record["sha256"] or
     profit.get("record",{}).get("ranking_eligible") is not False):
  raise ValueError("Detailed profit and income statement not from same original PDF")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  result={}
  for period,terms in EXPECTED.items():
   page=doc[terms["page"]-1]
   lines=[" ".join(v.split()) for v in page.get_text("text").splitlines() if v.strip()]
   if period not in " ".join(lines):raise ValueError("Expected period missing from PDF page")
   values={}
   for key,label in ALIASES.items():
    values[key]=find_table_amount(lines,label,terms[key])
   ni=values["net_interest_income"]["value_sgd_millions"]
   non=values["non_interest_income"]["value_sgd_millions"]
   result[period]={"pdf_page":terms["page"],"unit":"SGD_millions",
    "net_interest_income":ni,"non_interest_income":non,
    "combined_interest_and_noninterest_income":ni+non,
    "operating_profit_before_allowances":values["operating_profit_before_allowances"]["value_sgd_millions"],
    "allowances_charged":values["allowances_charged"]["value_sgd_millions"],
    "original_line_locations":{k:v["line"] for k,v in values.items()}}
 finally:doc.close()
 return {"schema_version":"sgx-ocbc-bank-income-components-v154",
  "symbol":"O39","period_end_date":"2026-09-30",
  "original_pdf_sha256":record["sha256"],"original_pdf_url":record["official_sgx_original_url"],
  "bank_statements":result,
  "reported_income_components_arithmetically_added":True,
  "does_not_claim_all_income_is_interest_income":True,
  "same_issuer_primary_unaudited_2026_research":True,
  "independent_third_party_numerical_verification":False,
  "bank_loan_loss_full_reperformance":False,
  "validated_fy2025_audited_per":False,"current_quote_shares_verified":False,
  "ranking_eligible":False}

def main():
 p=argparse.ArgumentParser()
 for k in ("originals","profit","output"):p.add_argument("--"+k,required=True)
 a=p.parse_args()
 original=json.loads(Path(a.originals).read_text())
 earlier=json.loads(Path(a.profit).read_text())
 output={"schema_version":"sgx-ocbc-bank-components-probe-v154",
  "status":"NOT_VERIFIED","record":None,"error":None}
 try:
  orig=next(x for x in original["record"]["records"] if x["filename"]==NAME)
  output["record"]=extract(fetch_pdf(orig["official_sgx_original_url"]),original,earlier)
  output["status"]="OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED"
 except Exception as exc:output["error"]=type(exc).__name__+": "+str(exc)[:300]
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(output["status"],output["error"])
if __name__=="__main__":main()
