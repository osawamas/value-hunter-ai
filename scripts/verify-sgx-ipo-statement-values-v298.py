#!/usr/bin/env python3
"""v298 verify exact fiscal-period statement rows in SHA-pinned original PDFs.
The committed amounts are a reviewed extraction, not computed by guessing a
similarly named pro-forma table, and are never promoted into a quote/rank feed.
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import tempfile
import urllib.request
import datetime

ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("v297",ROOT/"scripts/replay-sgx-ipo-financial-pdfs-v297.py")
v297=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v297)

LABELS={
 "revenue":r"^\s*Revenue\s+",
 "gross_profit":r"^\s*Gross profit\s+",
 "profit_for_year":r"^\s*Profit for the (?:financial )?year(?:/period)?\s+",
 "total_equity":r"^\s*Total equity\s+"
}
def values_from_row(line,label,count):
 pattern=LABELS[label]
 if not re.match(pattern,line,re.IGNORECASE):return None
 rest=re.sub(pattern,"",line,count=1,flags=re.IGNORECASE)
 tokens=re.findall(r"(?<!\w)\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|(?<!\w)\(?-?\d+(?:\.\d+)?\)?",rest)
 if len(tokens)!=count or any("." in x or "(" in x for x in tokens):return None
 return [int(x.replace(",","")) for x in tokens]
def verify_section(text,record):
 lines=text.splitlines()
 if record["symbol"]=="9DC":
  anchor="SELECTED COMBINED FINANCIAL INFORMATION"
  start=next((i for i,x in enumerate(lines) if x.strip()==anchor),-1)
  if start<0:raise ValueError("9DC audited financial section missing")
  end=next((i for i in range(start+1,len(lines)) if lines[i].strip()=="SELECTED PRO FORMA COMBINED FINANCIAL INFORMATION"),-1)
  if end<0 or end-start>450:raise ValueError("Audited/pro forma boundary missing")
  scope=lines[start:end]
  top=" ".join(scope[:24])
  if "Audited" not in top or "FY2024" not in top or "FY2026" not in top:
   raise ValueError("9DC column scope not marked audited FY2024-FY2026")
  periods=record["periods"]
 else:
  anchor="SUMMARY COMBINED STATEMENTS OF PROFIT OR LOSS AND OTHER COMPREHENSIVE"
  start=next((i for i,x in enumerate(lines) if x.strip().startswith(anchor)), -1)
  if start<0:raise ValueError("MIM combined audited/unaudited table missing")
  scope=lines[start:start+210]
  top=" ".join(scope[:22])
  if "Audited" not in top or "Unaudited" not in top or "2023" not in top or "2026" not in top:
   raise ValueError("MIM five-column audited/unaudited scope missing")
  periods=record["periods"]+record["interim"]
 counts={label:0 for label in LABELS}
 for label in LABELS:
  expected=[x[label] for x in periods]
  if any(x is None for x in expected):
   # MIM's equity snapshot has four columns (2023, 2024, 2025, 2026-H1),
   # unlike the five-column income statement (which has both H1 years).
   if label!="total_equity" or record["symbol"]!="MIM":
    raise ValueError("Missing unexpectedly required financial figure")
   expected=[periods[i][label] for i in [0,1,2,4]]
  for line in scope:
   row=values_from_row(line,label,len(expected))
   if row is not None and row==expected:counts[label]+=1
  if counts[label]==0 and record["symbol"]=="MIM" and label=="profit_for_year":
   # PDF text layout breaks the printed heading into two lines for "Profit
   # for the financial year/period". Require a matching numerical row and
   # explicit nearby profit-for-period heading, not owner-attributable totals.
   number_sequence=r"\s+".join(re.escape(f"{v:,}") for v in expected)
   candidates=[i for i,line in enumerate(scope) if re.search(number_sequence,line) and
     re.search(r"profit\s+for\s+(?:the\s+)?(?:financial\s+)?(?:year|period)",
       " ".join(scope[max(0,i-3):i+1]),re.I)]
   if len(candidates)==1:counts[label]=1
  if counts[label]!=1:raise ValueError(record["symbol"]+" audited scope row mismatch: "+label+
    " expected "+str(expected)+" matched "+str(counts[label]))
 if record["symbol"]=="9DC":
  pro=record["rejected_lookalike_pro_forma"]
  pro_scope=lines[end:end+800]
  for label in ["revenue","gross_profit","profit_for_year"]:
   if not any(values_from_row(line,label,1)==[pro[label]] for line in pro_scope):
    raise ValueError("9DC excluded unaudited pro forma value not corroborated: "+label)
 return {"symbol":record["symbol"],"fiscal_years":len(record["periods"]),
  "interim_periods":len(record.get("interim",[])),
  "rows_confirmed":counts,
  "audit_scope_safe":True,"pro_forma_investment_figures_used":False,
  "rank_eligible":False}

def download(source):
 req=urllib.request.Request(source["url"],headers={
  "User-Agent":"VALUE-HUNTER-AI-source-validation/1.0 (+https://github.com/osawamas/value-hunter-ai)",
  "Accept":"application/pdf"})
 with urllib.request.urlopen(req,timeout=45) as reply:
  if not reply.geturl().startswith("https://links.sgx.com/"):
   raise ValueError("Unexpected non-SGX redirect")
  blob=reply.read(v297.MAX_BYTES+1)
 if hashlib.sha256(blob).hexdigest()!=source["github_actions_confirmed_sha256"] or len(blob)!=source["github_actions_confirmed_original_bytes"]:
  raise ValueError("Verified PDF checksum drift")
 return blob
def main():
 manifest=json.loads((ROOT/"docs/data/sgx-ipo-financial-documents-v297.json").read_text())
 sources=v297.validate_manifest(manifest)
 financial=json.loads((ROOT/"docs/data/sgx-ipo-audited-historical-v298.json").read_text())
 if financial["schema_version"]!="sgx-ipo-audited-historical-financials-v298" or financial["ranking_eligible_count"]!=0 or financial["ranking_enabled"] is not False:
  raise ValueError("Research schema/ranking state changed")
 out=[]
 for record in financial["issuers"]:
  source=next(x for x in sources if x["symbol"]==record["symbol"] and x["document_type"]=="REGISTERED_IPO_PROSPECTUS")
  if record["source_pdf_sha256"]!=source["github_actions_confirmed_sha256"] or record["source_pdf_url"]!=source["url"]:
   raise ValueError("Audited statement evidence mismatch")
  raw=download(source)
  with tempfile.TemporaryDirectory() as temp:
   pdf=pathlib.Path(temp)/"original.pdf";pdf.write_bytes(raw)
   proc=subprocess.run(["pdftotext","-layout",str(pdf),"-"],capture_output=True,timeout=65,check=True)
   text=proc.stdout.decode("utf-8",errors="replace")
  result=verify_section(text,record)
  result["original_pdf_sha256"]=source["github_actions_confirmed_sha256"]
  out.append(result)
  print("v298 "+result["symbol"]+" VERIFIED original SHA + audited table revenue/gross/PAT/equity; periods="+str(result["fiscal_years"])+" audited, "+str(result["interim_periods"])+" unaudited")
 report={"schema_version":"sgx-ipo-original-audited-financial-reconciliation-v298",
  "checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "sources":out,"all_source_tables_reconciled":len(out)==2,
  "pro_forma_not_used":True,"live_market_data_licence_verified":False,
  "independent_current_financial_reverification":False,"ranking_eligible_count":0}
 dest=ROOT/"build/research/sgx-ipo-audited-reconciliation-v298.json"
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
