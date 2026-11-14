"""v130: independent FY2025 audit report evidence in G13 SGX annual report.

Direct confirmation of auditor's stated opinion and scope within the annual
report, distinct from an independently reproduced set of accounting numbers.
Cannot certify unaudited 2026 interim data or market quote.
"""
import argparse,hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen

def parse(raw, feed):
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
  raise ValueError("Not a genuine PDF")
 if feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_eligible_count")!=0:
  raise ValueError("Financial feed not safe")
 found=[r for r in feed.get("records",[]) if r.get("symbol")=="G13"]
 if len(found)!=1:raise ValueError("G13 issuer record not unique")
 r=found[0]
 from g13_balance_v42 import SOURCE as G13_BALANCE_SOURCE
 if r.get("financial_source_url")!=G13_BALANCE_SOURCE:
  raise ValueError("Source mismatch")
 sha=hashlib.sha256(raw).hexdigest()
 if r.get("financial_pdf_sha256")!=sha:
  raise ValueError("Actual SGX original differs from published annual PDF hash")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  text=[ " ".join(page.get_text("text").replace("’","'").split()) for page in doc ]
 finally:
  doc.close()
 evidence=[]
 for ix,page in enumerate(text):
  if ("INDEPENDENT AUDITOR'S REPORT" in page.upper() and
      ("Our opinion" in page or "In our opinion" in page)):
   evidence.append((ix+1,page))
 if not evidence:
  raise ValueError("Actual independent auditor opinion missing")
 combined=" ".join(p for _,p in evidence)
 # Auditor-opinion pages are in the financial-year section, not other reporting sections.
 if not re.search(r"consolidated financial statements of Genting Singapore Limited",combined,re.I):
  raise ValueError("Audited legal entity not identified")
 if not re.search(r"true and fair view",combined,re.I):
  raise ValueError("Audit opinion wording missing")
 if not re.search(r"31 December 2025",combined,re.I):
  raise ValueError("Audit period not established")
 if not any("We are independent of the Group" in page for page in text):
  raise ValueError("Independence declaration missing")
 if not any("PricewaterhouseCoopers LLP" in page for page in text):
  raise ValueError("Audit firm identity missing")
 # Existing FY2025 figures must appear in the actual audited annual report,
 # but this is not a third-party independent reconstruction of those values.
 whole=" ".join(text)
 for n in ("2,452,053","390,346","8,205,416"):
  if n not in whole:raise ValueError("Published FY2025 figures missing from report")
 return {
  "schema_version":"sgx-g13-fy2025-independent-auditor-opinion-v130",
  "symbol":"G13","fiscal_year":2025,
  "source_url":r["financial_source_url"],"source_pdf_sha256":sha,
  "auditor_issuer":"PricewaterhouseCoopers LLP",
  "auditor_independence_statement_observed":True,
  "independent_auditor_opinion_found":True,
  "audited_annual_group_financials_period_end":"2025-12-31",
  "report_pages_containing_auditor_opinion":[i for i,_ in evidence],
  "reported_annual_revenue_sgd_thousands":r["revenue_sgd_thousands"],
  "reported_attributable_profit_sgd_thousands":r["attributable_profit_sgd_thousands"],
  "reported_group_equity_sgd_thousands":r["equity_sgd_thousands"],
  "independent_numerical_recalculation_by_our_system":False,
  "2026_interim_figures_audited_by_this_opinion":False,
  "2026_stock_price_or_current_shares_audited":False,
  "ranking_eligible":False,"financial_feed_modified":False
 }

def fetch(url):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0",
                         "Accept":"application/pdf"})
 with urlopen(req,timeout=45) as r:
  if r.geturl()!=url:raise ValueError("Original SGX PDF redirected")
  raw=r.read(22_000_001)
 if not raw.startswith(b"%PDF") or len(raw)>22_000_000:
  raise ValueError("Annual report PDF invalid or oversized")
 return raw

def main():
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 feed=json.loads(Path(a.feed).read_text())
 q=[x for x in feed["records"] if x["symbol"]=="G13"][0]
 result={"schema_version":"sgx-g13-fy2025-auditor-probe-v130",
         "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
         "source_url":q["financial_source_url"],"status":"NOT_VERIFIED",
         "record":None,"error":None}
 try:
  result["record"]=parse(fetch(q["financial_source_url"]),feed)
  result["status"]="INDEPENDENT_FY2025_AUDITOR_OPINION_IN_PRIMARY_PDF_CONFIRMED"
 except Exception as e:
  result["error"]=type(e).__name__+": "+str(e)[:280]
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(result["status"],result["error"])
if __name__=="__main__":main()
