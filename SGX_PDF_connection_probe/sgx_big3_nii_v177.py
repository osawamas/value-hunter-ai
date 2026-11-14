"""v177: 3Q26 Singapore Big Three banks' NII from actual SGX originals.

DBS 3Q trading-update PDF primary exact NII, OCBC issuer original exact
Q3, and UOB issuer original quarter table. The 8,302m sum is simple
arithmetic, NOT independent bank financial auditing or stock valuation.
"""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
URL="https://links.sgx.com/FileOpen/3Q26_trading_update.ashx?App=Announcement&FileID=910439"
def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI primary SGX D05 NII","Accept":"application/pdf"})
 with urlopen(req,timeout=35) as response:
  path=urlparse(response.geturl())
  if path.scheme!="https" or path.hostname!="links.sgx.com" or not path.path.startswith("/FileOpen/") or "pdf" not in response.headers.get("Content-Type","").lower():
   raise ValueError("SGX D05 trading PDF source not preserved")
  return response.read(12_000_001)
def combine(raw,dbs,ocbc,uob):
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):raise ValueError("DBS SGX primary not a PDF")
 if (dbs.get("status")!="DBS_3Q26_PRIMARY_SGX_ANNOUNCEMENT_AND_PDF_VERIFIED" or
     ocbc.get("schema_version")!="sgx-ocbc-bank-research-bundle-v166" or
     uob.get("status")!="UOB_3Q26_9M26_SGX_PRIMARY_TABLE_COLUMNS_VERIFIED"):
  raise ValueError("Original issuer financial material missing")
 d=dbs["record"];u=uob["record"]
 if d.get("symbol")!="D05" or d.get("financial_period_end")!="2026-09-30" or d.get("per_pbr_ranking_permitted") is not False:
  raise ValueError("DBS SGX issuer profile incorrect")
 if (ocbc.get("symbol")!="O39" or ocbc.get("quarter_end")!="2026-09-30" or
     ocbc.get("per_pbr_and_ranking_permitted") is not False or
     ocbc.get("independent_third_party_financial_reperformance") is not False):
  raise ValueError("OCBC issuer PDF not independently verified")
 if (u.get("symbol")!="U11" or u.get("financial_period_end")!="2026-09-30" or
     u.get("ranking_eligible") is not False or
     u.get("table_row_and_column_mapping_verified_in_issuer_pdf") is not True):
  raise ValueError("UOB exact table source absent")
 import fitz
 pdf=fitz.open(stream=raw,filetype="pdf")
 try:
  n=len(pdf);text=" ".join(" ".join(page.get_text("text") for page in pdf).split())
 finally:pdf.close()
 if not 2<=n<=100 or not re.search(r"(?:3rd|Third)\s+Quarter\s+2026",text,re.I):
  raise ValueError("DBS Q3 trading update period missing")
 for label,pattern in [("net interest income",r"Net interest income"),
                        ("3Q26 group NII exact",r"\b3,711\b"),
                        ("9M26 group NII exact",r"\b10,786\b"),
                        ("3Q total income",r"\b5,845\b")]:
  if not re.search(pattern,text,re.I):raise ValueError("DBS official PDF missing "+label)
 ocbc_nii=ocbc.get("income_statement_sgd_millions",{}).get("3Q26",{}).get("net_interest_income")
 uob_nii=u.get("period_specific_table_rows",{}).get("Net interest income",{}).get("3q26")
 if ocbc_nii!=2313 or uob_nii!=2278:raise ValueError("Other primary SGX quarter sources disagree")
 dbs_nii=3711
 if dbs_nii+ocbc_nii+uob_nii!=8302:raise ValueError("Three-bank source arithmetic mismatch")
 return {"schema_version":"sgx-big3-nii-source-consistency-v177",
  "financial_period_end":"2026-09-30","unit":"SGD_millions",
  "dbs_official_trading_pdf_url":URL,"dbs_official_trading_pdf_sha256":hashlib.sha256(raw).hexdigest(),
  "dbs_original_slide_source_sha256":d["official_pdf_sha256"],
  "ocbc_official_pdf_sha256":ocbc["sgx_original_pdf_sha256"],
  "uob_official_pdf_sha256":u["official_pdf_sha256"],
  "bank_net_interest_income_3q26":{"D05":3711,"O39":2313,"U11":2278},
  "three_bank_3q26_nii_sum_sgd_millions":8302,
  "source_date_and_unit_consistent":True,
  "dbs_trading_pdf_exact_amount_observed":True,
  "dbs_trading_pdf_single_table_row_column_reperformance_completed":False,
  "sgx_editorial_market_update_reference":"https://www.sgx.com/research-education/market-updates/20261106-sti-banks-report-16th-consecutive-quarter-s8b-nii",
  "sgx_editorial_update_html_fetched_by_pipeline":False,
  "independent_third_party_earnings_audit":False,
  "current_sgx_trade_quote_or_treasury_shares_verified":False,
  "ranking_eligible":False}
def main():
 p=argparse.ArgumentParser()
 for k in ("dbs","ocbc","uob","output"):p.add_argument("--"+k,required=True)
 a=p.parse_args()
 inputs=[json.loads(Path(getattr(a,k)).read_text()) for k in ("dbs","ocbc","uob")]
 out={"schema_version":"sgx-big3-nii-probe-v177","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=combine(fetch(),*inputs)
  out["status"]="SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:270]
 t=Path(a.output);t.parent.mkdir(parents=True,exist_ok=True)
 t.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
