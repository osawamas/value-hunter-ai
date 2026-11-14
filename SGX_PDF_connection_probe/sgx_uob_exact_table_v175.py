"""v175: table-row + 9M/3Q exact UOB 2026 source column validation.

Issuer original SGX CFO PDF page 3, columns 9M26 / 9M25 / 3Q26 / 3Q25.
NOT independent third-party accounting or current security valuation.
"""
import argparse,hashlib,json
from pathlib import Path
from sgx_uob_table_v174 import source

ROWS={
 "Net interest income":(6900,7009,2278,2265),
 "Net fee income":(2035,1945,733,615),
 "Total income":(10398,10519,3381,3398),
 "Net profit":(4165,3271,1250,443)
}
def row(lines,label,expected):
 positions=[i for i,line in enumerate(lines) if line.strip()==label]
 if len(positions)!=1:raise ValueError("Ambiguous income table row "+label)
 start=positions[0]+1
 if start+7>=len(lines):raise ValueError("Missing comparison columns")
 values=lines[start:start+8]
 for index,amount in zip((0,1,3,6),expected):
  if values[index]!=f"{amount:,}":
   raise ValueError("Incorrect 9M/3Q amount or shifted source column: "+label)
 return {"9m26":expected[0],"9m25":expected[1],
  "3q26":expected[2],"3q25":expected[3],
  "pdf_page":3,"table_line":start,
  "original_eight_column_text":values}
def analyze(raw,prior,layout):
 if (prior.get("status")!="UOB_Q3_CFO_PRIMARY_SGX_PDF_VERIFIED" or
     layout.get("status")!="UOB_PRIMARY_CFO_FINANCIAL_ROW_CONTEXTS_IDENTIFIED"):
  raise ValueError("Original first-stage PDF or table rows missing")
 p=prior["record"];l=layout["record"]
 sha=hashlib.sha256(raw).hexdigest()
 if not raw.startswith(b"%PDF") or sha!=p["source_pdf_sha256"] or sha!=l["official_pdf_sha256"] or p["financial_period_end"]!="2026-09-30":
  raise ValueError("SGX PDF changed/identity invalid")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)!=p["source_pdf_page_count"]:raise ValueError("PDF pages changed")
  lines=[" ".join(x.split()) for x in doc[2].get_text("text").splitlines() if x.strip()]
  if not all(x in " ".join(lines) for x in ("9M26","9M25","3Q26","3Q25")):
   raise ValueError("Original SGX columns not labeled with intended quarters")
  values={name:row(lines,name,expected) for name,expected in ROWS.items()}
 finally:doc.close()
 if values["Net profit"]["3q26"]!=p["cfo_pdf_observed_group_net_profit_3q26_sgd_millions"] or values["Net profit"]["9m26"]!=p["cfo_pdf_observed_group_net_profit_9m26_sgd_millions"]:
  raise ValueError("Verified source row does not equal earlier summary")
 return {"schema_version":"sgx-uob-exact-3q26-bank-statement-v175",
  "symbol":"U11","financial_period_end":"2026-09-30","unit":"SGD_millions",
  "official_pdf_url":p["source_pdf_url"],"official_pdf_sha256":sha,
  "financial_table_pdf_page":3,
  "period_specific_table_rows":values,
  "table_row_and_column_mapping_verified_in_issuer_pdf":True,
  "independent_third_party_numerical_reperformance":False,
  "2026_interim_audited_under_fy2025_opinion":False,
  "2026_11_13_buyback_original_verified":False,
  "current_sgx_quote_and_treasury_shares_verified":False,
  "ranking_eligible":False}
def main():
 parser=argparse.ArgumentParser()
 for x in ("prior","layout","output"):parser.add_argument("--"+x,required=True)
 a=parser.parse_args()
 prior=json.loads(Path(a.prior).read_text());layout=json.loads(Path(a.layout).read_text())
 out={"schema_version":"sgx-uob-column-precision-probe-v175","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=analyze(source(),prior,layout)
  out["status"]="UOB_3Q26_9M26_SGX_PRIMARY_TABLE_COLUMNS_VERIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:260]
 f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
 f.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
