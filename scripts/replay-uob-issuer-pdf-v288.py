#!/usr/bin/env python3
"""v288: replay UOB issuer-hosted official 3Q26 PDF (same issuer, independent delivery).
No trading prices. Use strict labelled net profit and net interest-income rows.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import urllib.error
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent.parent
URL="https://www.uob.com.sg/investor-relations/assets/pdfs/investor/financial/2026/performance-highlights-3q-2026.pdf"
MAX_BYTES=8_000_000
def get_source():
 data=json.loads((ROOT/"docs/data/sgx-big3-bank-research-v186.json").read_text())
 if data["schema_version"]!="sgx-big3-normalized-bank-quarters-v186" or data["period_end"]!="2026-09-30" or data["ranking_eligible"] is not False:
  raise ValueError("SGX bank research source drift")
 entries=[x for x in data["entries"] if x["symbol"]=="U11"]
 if len(entries)!=1 or (entries[0]["q3profit"],entries[0]["nineprofit"],entries[0]["q3nii"],entries[0]["ninenii"])!=(1250,4165,2278,6900):
  raise ValueError("UOB original expected values changed")
 return entries[0]
def check_text(text,record):
 upper=text.upper()
 # Search actual same labelled table row (not numbers floating elsewhere on page);
 # 9M26 value is first and 3Q26 value is 4th (per issuer results highlights).
 labels={
  "profit":("NET PROFIT",record["nineprofit"],record["q3profit"]),
  "nii":("NET INTEREST INCOME",record["ninenii"],record["q3nii"])
 }
 checks={}
 for key,(label,nine,three) in labels.items():
  rows=[]
  for line in upper.splitlines():
   if re.search(r"(?<![A-Z])"+re.escape(label)+r"(?![A-Z])",line):
    pieces=re.findall(r"(?<![0-9])(?:\d{1,3},\d{3}|\d{1,4})(?![0-9])",line)
    values=[int(z.replace(",","")) for z in pieces]
    rows.append(values)
  checks[key]=any(len(a)>=5 and a[0]==nine and a[3]==three for a in rows)
 return {"exact_labeled_issuer_pdf_table_rows_match":all(checks.values()),
  "labeled_table_checks":checks,
  "same_issuer_different_publication_not_third_party_audit":True,
  "issuer_full_financial_audit_complete":False,
  "licensed_quote_and_latest_shares_complete":False,
  "ranking_eligible":False}
def replay():
 record=get_source()
 pdf=b"";error=None;checks={"exact_labeled_issuer_pdf_table_rows_match":False}
 try:
  request=urllib.request.Request(URL,headers={
   "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
   "Accept":"application/pdf"})
  with urllib.request.urlopen(request,timeout=25) as response:
   if response.geturl()!=URL:raise ValueError("Unexpected redirect")
   pdf=response.read(MAX_BYTES+1)
   if len(pdf)>MAX_BYTES or not pdf.startswith(b"%PDF-"):raise ValueError("Not a bounded PDF")
  if not shutil.which("pdftotext"):raise ValueError("pdftotext unavailable")
  result=subprocess.run(["pdftotext","-layout","-","-"],input=pdf,capture_output=True,timeout=25)
  if result.returncode!=0:raise ValueError("pdftotext failure")
  checks=check_text(result.stdout.decode("utf-8",errors="replace"),record)
 except (OSError,ValueError,urllib.error.URLError,TimeoutError,subprocess.TimeoutExpired) as exc:
  error=type(exc).__name__
 output={"schema_version":"uob-2026-3q-issuer-pdf-secondary-delivery-v288",
  "captured_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
  "issuer":"UOB","symbol":"U11","date":"2026-09-30",
  "issuer_owned_pdf_url":URL,"source_pdf_sha256":hashlib.sha256(pdf).hexdigest() if pdf else None,
  "source_pdf_bytes":len(pdf),"source_error":error,
  "sgx_pdf_url":record["source"],"sgx_pdf_sha256":record["sha"],
  "source_numbers":{"q3profit":record["q3profit"],"nineprofit":record["nineprofit"],
     "q3nii":record["q3nii"],"ninenii":record["ninenii"]},
  "checks":checks,"third_party_independent_audit_verified":False,
  "licensed_market_quote_verified":False,"latest_share_count_verified":False,
  "ranking_eligible_count":0}
 target=ROOT/"build/research/uob-issuer-pdf-secondary-v288.json"
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
 print("v288 "+("ISSUER_HOSTED_EXACT_TABLE_PASS" if checks["exact_labeled_issuer_pdf_table_rows_match"] else "NOT_RECONCILED")+
  " bytes="+str(len(pdf))+" sha256="+str(output["source_pdf_sha256"]))
if __name__=="__main__":replay()
