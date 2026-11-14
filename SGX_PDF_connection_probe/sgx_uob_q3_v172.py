"""v172: UOB direct original SGX FileOpen CFO 3Q26 reporting research.

Only a genuine 4-Nov original SGX PDF attachment, not proof of its
corporate announcement landing-page ref or 13-Nov treasury shares.
"""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen

PDF="https://links.sgx.com/FileOpen/3Q26%20CFO%20presentation%20slides.ashx?App=Announcement&FileID=910319"
def fetch():
 req=Request(PDF,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 UOB original evidence",
  "Accept":"application/pdf"})
 with urlopen(req,timeout=35) as resp:
  u=urlparse(resp.geturl())
  if u.scheme!="https" or u.hostname!="links.sgx.com" or not u.path.startswith("/FileOpen/") or "pdf" not in resp.headers.get("Content-Type","").lower():
   raise ValueError("SGX official PDF redirect integrity missing")
  return resp.read(12_000_001)

def analyze(pdf):
 if not isinstance(pdf,bytes) or not pdf.startswith(b"%PDF") or len(pdf)>12_000_000:
  raise ValueError("SGX original not returned")
 import fitz
 document=fitz.open(stream=pdf,filetype="pdf")
 try:
  pages=len(document)
  if not 2<=pages<=80:raise ValueError("Unexpected original slide count")
  text=" ".join(" ".join(page.get_text("text") for page in document).split())
 finally:document.close()
 for name,pattern in (
  ("UOB",r"\bUOB\b"),
  ("3Q26",r"\b3Q26\b"),
  ("9M26",r"\b9M26\b"),
  ("3Q net profit",r"\b1,250\b"),
  ("9M net profit",r"\b4,165\b"),
  ("3Q net interest income",r"\b2,278\b"),
  ("3Q net fee",r"\b733\b"),
  ("quarter table columns",r"3Q25")):
  if not re.search(pattern,text,re.I):raise ValueError("UOB CFO PDF missing "+name)
 # Exact source positions verified only when tabular row/column-scoped parser is added.
 return {"schema_version":"sgx-uob-q3-cfo-original-v172",
  "symbol":"U11","issuer":"UNITED OVERSEAS BANK LIMITED",
  "financial_period_end":"2026-09-30",
  "source_pdf_url":PDF,"source_pdf_sha256":hashlib.sha256(pdf).hexdigest(),
  "source_pdf_page_count":pages,
  "issuer_original_sgx_pdf_verified":True,
  "announcement_landing_page_and_ref_verified":False,
  "cfo_pdf_observed_group_net_profit_3q26_sgd_millions":1250,
  "cfo_pdf_observed_group_net_profit_9m26_sgd_millions":4165,
  "cfo_pdf_observed_net_interest_income_3q26_sgd_millions":2278,
  "cfo_pdf_observed_net_fee_income_3q26_sgd_millions":733,
  "exact_table_row_column_scoping_independently_reperformed":False,
  "issuer_2026_interim_independently_audited":False,
  "nov13_buyback_announcement_original_verified":False,
  "independent_third_party_financial_verification":False,
  "current_sgx_quote_verified":False,
  "current_treasury_adjusted_shares_verified":False,
  "ranking_eligible":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
 out={"schema_version":"sgx-uob-q3-cfo-probe-v172","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=analyze(fetch())
  out["status"]="UOB_Q3_CFO_PRIMARY_SGX_PDF_VERIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:250]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
