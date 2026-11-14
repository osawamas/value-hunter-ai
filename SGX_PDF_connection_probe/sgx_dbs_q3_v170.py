"""v170: original SGX D05 3Q26 announcement + CFO presentation.

Verify both original hostnames, issuer/ticker/ISIN/SGX reference, PDF,
document hash and stated quarter performance. This is *issuer reported*
and NOT independent bank earnings validation or verified stock quote.
"""
import argparse,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen

ANNOUNCEMENT="https://links.sgx.com/1.0.0/corporate-announcements/PWUTJ371L9ASOMF8/3044419f7294ad033fa90ebb2386da5245d415e663ece3af98d4448469034599"
PDF_URL="https://links.sgx.com/FileOpen/3Q26_CFO_presentation.ashx?App=Announcement&FileID=910441"
REF="SG261105OTHRTOOX"
ISIN="SG1L01001701"
class Extract(HTMLParser):
 def __init__(self):super().__init__();self.data=[];self.hidden=0
 def handle_starttag(self,t,attrs):
  if t in ("script","style"):self.hidden+=1
  if t in ("div","p","td","tr","h1","h2","span","li","br"):self.data.append(" ")
 def handle_endtag(self,t):
  if t in ("script","style") and self.hidden:self.hidden-=1
 def handle_data(self,s):
  if not self.hidden:self.data.append(s)
def fetch(url,expected_pdf=False):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 original SGX bank audit",
                           "Accept":"application/pdf" if expected_pdf else "text/html"})
 with urlopen(req,timeout=32) as response:
  parsed=urlparse(response.geturl());origin=urlparse(url)
  if parsed.scheme!="https" or parsed.hostname!="links.sgx.com" or origin.hostname!="links.sgx.com":
   raise ValueError("SGX source redirected to non-SGX host")
  if expected_pdf:
   if "pdf" not in response.headers.get("Content-Type","").lower() or not parsed.path.startswith("/FileOpen/"):
    raise ValueError("Not SGX original PDF")
  else:
   if "html" not in response.headers.get("Content-Type","").lower() or parsed.path!=origin.path:
    raise ValueError("Not original SGX corporate announcement HTML")
  raw=response.read(10_000_001)
 if not 300<len(raw)<=10_000_000:raise ValueError("SGX response empty or too large")
 return raw
def analyze(html,pdf):
 if not isinstance(html,bytes) or not isinstance(pdf,bytes) or not pdf.startswith(b"%PDF"):
  raise ValueError("Original SGX announcement or PDF missing")
 p=Extract();p.feed(html.decode("utf-8","replace"))
 text=" ".join(" ".join(p.data).split())
 for key,pattern in (
  ("issuer",r"Issuer\s*/\s*Manager\s+DBS GROUP HOLDINGS LTD"),
  ("symbol",r"DBS GROUP HOLDINGS LTD\s*-\s*"+ISIN+r"\s*-\s*D05\b"),
  ("ref",r"Announcement Reference\s+"+REF+r"\b"),
  ("date",r"05-Nov-2026\s+06:30:36"),
  ("period",r"For Financial Period Ended\s+30/09/2026"),
  ("attachment",r"3Q26_CFO_presentation\.pdf")):
  if not re.search(pattern,text,re.I):raise ValueError("SGX issuer announcement does not show "+key)
 import fitz
 d=fitz.open(stream=pdf,filetype="pdf")
 try:
  count=len(d)
  content=" ".join(" ".join(page.get_text("text") for page in d).split())
 finally:d.close()
 if not 2<=count<=100:raise ValueError("Invalid original DBS slide length")
 for metric,pattern in (
  ("3Q group profit",r"2\.81\s*(?:b|billion)"),
  ("9M group profit",r"8\.82\s*(?:b|billion)"),
  ("net interest income",r"3\.71\s*(?:b|billion)"),
  ("nonperforming loans",r"0\.9\s*%"),
  ("transitional CET1",r"15\.9\s*%")):
  if not re.search(pattern,content,re.I):raise ValueError("Missing DBS 3Q bank source metric "+metric)
 return {"schema_version":"sgx-dbs-q3-2026-original-bank-research-v170",
  "symbol":"D05","issuer":"DBS GROUP HOLDINGS LTD","isin":ISIN,
  "announcement_reference":REF,"broadcast_sgt":"2026-11-05 06:30:36",
  "financial_period_end":"2026-09-30",
  "announcement_source_url":ANNOUNCEMENT,"announcement_html_sha256":hashlib.sha256(html).hexdigest(),
  "official_pdf_url":PDF_URL,"official_pdf_sha256":hashlib.sha256(pdf).hexdigest(),
  "official_pdf_pages":count,
  "group_net_profit_3q26_sgd_billion_reported":"2.81",
  "group_net_profit_9m26_sgd_billion_reported":"8.82",
  "group_net_interest_income_3q26_sgd_billion_reported":"3.71",
  "npl_ratio_3q26_pct_reported":"0.9",
  "transitional_cet1_3q26_pct_reported":"15.9",
  "rounded_company_issuer_figures":True,
  "independent_earnings_reperformance":False,
  "quarterly_2026_independently_audited":False,
  "current_sgx_price_and_shares_verified":False,
  "per_pbr_ranking_permitted":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 args=p.parse_args()
 out={"schema_version":"sgx-dbs-q3-original-probe-v170","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=analyze(fetch(ANNOUNCEMENT),fetch(PDF_URL,True))
  out["status"]="DBS_3Q26_PRIMARY_SGX_ANNOUNCEMENT_AND_PDF_VERIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:250]
 dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
