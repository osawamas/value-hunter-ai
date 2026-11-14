"""v180: source-hash-bound DBS actual 3Q and 9M SGX bank financial table.

Page 7 of original SGX trading update: explicit 'Of which: Net interest
income' and 'Net profit' table rows; guards current and previous quarter
columns, plus two preceding component lines 3576+135=3711.
This is issuer-original historical arithmetic, NOT an independent audit.
"""
import argparse, hashlib, json
from pathlib import Path
from sgx_big3_nii_v177 import fetch,URL

def find_unique(lines,label,values):
 matches=[i for i,l in enumerate(lines) if l.strip()==label]
 if len(matches)!=1:raise ValueError("Missing or ambiguous original DBS table row: "+label)
 idx=matches[0]
 observed=lines[idx+1:idx+1+len(values)]
 if observed!=values:raise ValueError(label+" values are not in prescribed SGX original table columns")
 return {"original_pdf_page":7,"label":label,"row_index":idx,
         "source_column_values":observed}

def analyze(raw,prior,layout):
 if (prior.get("status")!="SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED" or
     layout.get("status")!="DBS_SGX_PRIMARY_TRADING_TABLE_CONTEXTS_CAPTURED"):
  raise ValueError("Original SGX source chain missing")
 p=prior["record"];q=layout["record"]
 sha=hashlib.sha256(raw).hexdigest()
 if (not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or
     sha!=p.get("dbs_official_trading_pdf_sha256") or
     sha!=q.get("original_trading_pdf_sha256") or
     q.get("exact_row_column_validation_completed") is not False):
  raise ValueError("Original trading PDF version not identical")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)<7:raise ValueError("Original financial statement page missing")
  lines=[" ".join(z.split()) for z in doc[6].get_text("text").splitlines() if z.strip()]
 finally:doc.close()
 # Printed order: 3Q26 3Q25 YoY 2Q26 QoQ 9M26 9M25 YoY.
 labels={
 "Of which: Net interest income":["3,711","3,578","4","3,581","4","10,786"],
 "Net profit":["2,813","2,954","(5)","3,079","(9)","8,822","8,675","2"],
 "Total income":["5,845","5,932","(1)","6,093","(4)","17,886","17,569","2"]
 }
 result={k:find_unique(lines,k,v) for k,v in labels.items()}
 hits=[i for i,z in enumerate(lines) if z.strip()=="Net interest income"]
 if len(hits)!=2:raise ValueError("Missing NII constituent account rows")
 first=lines[hits[0]+1:hits[0]+9]
 second=lines[hits[1]+1:hits[1]+8]
 if first[:2]!=["3,576","3,558"] or second[:2]!=["135","20"]:
  raise ValueError("Distinct NII component rows not matching SGX original")
 if 3576+135!=3711 or 2813>5845:raise ValueError("Exact bank source consistency failed")
 if result["Net profit"]["source_column_values"][0]!="2,813" or p["bank_net_interest_income_3q26"]["D05"]!=3711:
  raise ValueError("Issuer exact 3Q value inconsistent with prior verified v177")
 return {"schema_version":"sgx-dbs-exact-3q-9m-original-v180","symbol":"D05",
  "financial_period_end":"2026-09-30","unit":"SGD_millions",
  "original_sgx_pdf_url":URL,"original_pdf_sha256":sha,
  "statement_pdf_page":7,
  "official_table_column_order":["3Q26","3Q25","3Q26_YOY_PCT","2Q26","3Q26_QOQ_PCT","9M26","9M25","9M26_YOY_PCT"],
  "net_interest_row_only_first_six_column_values_authenticated":True,
  "exact_original_table_rows":result,
  "net_interest_income_3q26_components_sgd_millions":[3576,135],
  "net_interest_income_3q26_sgd_millions":3711,
  "net_profit_3q26_sgd_millions":2813,
  "net_profit_9m26_sgd_millions":8822,
  "income_3q26_sgd_millions":5845,
  "issuer_original_row_and_column_positions_verified":True,
  "independent_numerical_verification":False,
  "fy2025_auditor_opinion_does_not_certify_2026_interim":True,
  "official_execution_quote_verified":False,
  "latest_treasury_shares_verified":False,
  "ranking_eligible":False}

def main():
 a=argparse.ArgumentParser()
 for key in ("prior","layout","output"):a.add_argument("--"+key,required=True)
 args=a.parse_args()
 prior=json.loads(Path(args.prior).read_text())
 layout=json.loads(Path(args.layout).read_text())
 out={"schema_version":"sgx-dbs-exact-table-probe-v180","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=analyze(fetch(),prior,layout)
  out["status"]="DBS_3Q26_9M26_PRIMARY_SGX_TABLE_COLUMNS_RECONCILED"
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:300]
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
