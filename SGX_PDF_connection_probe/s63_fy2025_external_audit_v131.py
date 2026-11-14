"""v131: direct SGX independent S63 FY2025 auditor PDF.

Validate the independent audit opinion, issuer scope, period and explicit
revenue KAM figure. No inference about 2026, current market prices, or PER.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

SOURCE="https://links.sgx.com/FileOpen/ST%20Engineering%20Annual%20Report%202025.ashx?App=Announcement&FileID=880328"

def parse(raw,feed):
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or len(raw)>22_000_000:
  raise ValueError("Invalid original audit PDF bytes")
 if feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_eligible_count")!=0:
  raise ValueError("Untrusted feed state")
 rec=[r for r in feed.get("records",[]) if r.get("symbol")=="S63"]
 if len(rec)!=1 or rec[0].get("ranking_eligible") is not False or rec[0].get("fiscal_year")!=2025:
  raise ValueError("Not FY2025 S63 published metric record")
 if rec[0].get("financial_source_url")!=SOURCE or rec[0].get("financial_pdf_sha256")!=hashlib.sha256(raw).hexdigest():
  raise ValueError("Annual source URL or SHA mismatches published financial reference")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  texts=[" ".join(p.get_text("text").replace("’","'").split()) for p in doc]
 finally:doc.close()
 full=" ".join(texts)
 if not re.search(r"Independent Auditor's Report to the Members of Singapore Technologies Engineering Ltd",full,re.I):
  raise ValueError("Unrelated or missing audit report")
 if not re.search(r"Our Opinion.*?In our opinion.*?accompanying consolidated financial statements",full,re.I):
  raise ValueError("Consolidated audit opinion absent")
 if not re.search(r"true and fair view.*?31 December 2025",full,re.I):
  raise ValueError("FY2025 opinion scope absent")
 if not re.search(r"We are independent of the Group",full,re.I):
  raise ValueError("External auditor independence statement absent")
 if not re.search(r"PricewaterhouseCoopers LLP.*?Public Accountants and Chartered Accountants",full,re.I):
  raise ValueError("PwC audit signature missing")
 if not re.search(r"Singapore, 26 February 2026",full,re.I):
  raise ValueError("Audit signature date absent")
 # FY2025 audit key matter directly discusses revenue recognised.
 if not re.search(r"revenue of \$12,346,426,000",full,re.I):
  raise ValueError("Audited-revenue key audit matter absent")
 if rec[0].get("revenue_sgd_thousands")!=12346426:
  raise ValueError("Public FY2025 revenue differs from auditor's report KAM")
 return {
  "schema_version":"sgx-s63-fy2025-independent-audit-proof-v131",
  "symbol":"S63","source_url":SOURCE,
  "auditor_document_sha256":hashlib.sha256(raw).hexdigest(),
  "auditor":"PricewaterhouseCoopers LLP",
  "audit_fiscal_year":2025,"audit_reporting_period_end":"2025-12-31",
  "auditor_report_date":"2026-02-26",
  "audit_partner":"Lee Chian Yorn",
  "audit_opinion_scope_verified":True,
  "auditor_independence_statement_verified":True,
  "auditor_KAM_mentions_revenue_sgd":12346426000,
  "published_revenue_matches_auditor_KAM":True,
  "report_text_pages":len(texts),
  "independent_arithmetic_reperformance_completed":False,
  "parent_equity_independently_reconciled":False,
  "2026_nine_month_management_numbers_audited_by_this_opinion":False,
  "share_count_as_of_today_verified":False,
  "exchange_quote_verified":False,
  "ranking_eligible":False,
  "financial_feed_modified":False
 }

def fetch():
 req=Request(SOURCE,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 primary-audit-research",
                             "Accept":"application/pdf"})
 with urlopen(req,timeout=35) as resp:
  if resp.geturl()!=SOURCE or "pdf" not in resp.headers.get("Content-Type","").lower():
   raise ValueError("SGX audit original unavailable")
  raw=resp.read(22_000_001)
 if len(raw)>22_000_000 or not raw.startswith(b"%PDF"):
  raise ValueError("Invalid/oversized PDF response")
 return raw

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 feed=json.loads(Path(a.feed).read_text())
 out={"schema_version":"sgx-s63-auditor-probe-v131",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_url":SOURCE,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=parse(fetch(),feed)
  out["status"]="SGX_INDEPENDENT_S63_FY2025_AUDITOR_REPORT_CONFIRMED"
 except Exception as e:
  out["error"]=type(e).__name__+": "+str(e)[:250]
  try:
   import fitz
   pdf=fitz.open(stream=fetch(),filetype="pdf")
   try:
    raw_pages=[ " ".join(page.get_text("text").split()) for page in pdf ]
   finally:pdf.close()
   out["pdf_text_diagnostics"]={
    "page_count":len(raw_pages),
    "first_page_start":raw_pages[0][:1400] if raw_pages else "",
    "contains_opinion":any("opinion" in p.lower() for p in raw_pages),
    "contains_auditor":any("auditor" in p.lower() for p in raw_pages),
    "contains_pwc":any("PricewaterhouseCoopers" in p for p in raw_pages),
    "revenue_context":[p[max(0,p.find("12,346,426")-80):p.find("12,346,426")+120]
       for p in raw_pages if "12,346,426" in p][:3]
   }
  except Exception as inner:
   out["diagnostics_error"]=type(inner).__name__+": "+str(inner)[:200]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
