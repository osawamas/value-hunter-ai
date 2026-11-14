"""v143: original SGX OCBC 3Q2026 announcement identity and attachment manifest.

Announcement HTML metadata, not independently parsed Q3 accounting or verified
market-data. OCBC 12-Nov treasury use is a separate UNVERIFIED source.
"""
import argparse,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/"
ISIN="SG1S04926220"
REF="SG261106OTHRI4L9"
ATTACHMENTS=("OCBC_3Q26_Results_Press_Release.pdf",
             "OCBC_3Q26_CEO_Presentation.pdf",
             "OCBC_3Q26_Results_Highlights.pdf")
class Text(HTMLParser):
 def __init__(self):super().__init__();self.words=[];self.hide=0
 def handle_starttag(self,t,attrs):
  if t in ("script","style"):self.hide+=1
  if t in ("div","p","td","tr","span","h1","h2","h3","li","br"):self.words.append(" ")
 def handle_endtag(self,t):
  if t in ("script","style") and self.hide:self.hide-=1
  if t in ("div","p","td","tr","span","h1","h2","h3","li"):self.words.append(" ")
 def handle_data(self,s):
  if not self.hide:self.words.append(s)
def parse(raw):
 if not isinstance(raw,bytes) or not 400<len(raw)<3_000_000:raise ValueError("Invalid original SGX HTML")
 p=Text();p.feed(raw.decode("utf-8","replace"))
 s=" ".join(" ".join(p.words).split())
 required=[
  ("issuer",r"Issuer\s*/\s*Manager\s+OVERSEA-CHINESE BANKING CORPORATION LIMITED"),
  ("ISIN ticker",r"OVERSEA-CHINESE BANKING CORP\s*-\s*"+ISIN+r"\s*-\s*O39\b"),
  ("reference",r"Announcement Reference\s+"+REF+r"\b"),
  ("broadcast",r"Date\s*&\s*Time of Broadcast\s+06-Nov-2026\s+06:59:27\b"),
  ("report type",r"Financial Statements and Related Announcement"),
  ("quarter",r"Announcement Sub Title\s+Third Quarter Results"),
  ("period",r"For Financial Period Ended\s+30/09/2026")
 ]
 for name,pattern in required:
  found=re.findall(pattern,s,re.I)
  if not found or (name!="report type" and len(found)!=1):
   raise ValueError("Ambiguous/missing "+name)
 for name in ATTACHMENTS:
  if len(re.findall(re.escape(name),s,re.I))!=1:raise ValueError("Ambiguous/missing attachment "+name)
 return {"schema_version":"sgx-ocbc-2026q3-original-manifest-v143",
   "source_url":URL,"source_html_sha256":hashlib.sha256(raw).hexdigest(),
   "symbol":"O39","issuer":"OVERSEA-CHINESE BANKING CORPORATION LIMITED",
   "isin":ISIN,"announcement_reference":REF,
   "broadcast_sgt_text":"06-Nov-2026 06:59:27","financial_period_end":"2026-09-30",
   "attachments_listed":list(ATTACHMENTS),
   "sgx_original_announcement_identity_confirmed":True,
   "attached_pdfs_downloaded_and_numerically_parsed":False,
   "independent_financial_numbers_reperformed":False,
   "nov12_treasury_shares_notice_verified":False,
   "latest_share_count_verified":False,"exact_exchange_quote_verified":False,
   "market_cap_per_pbr_eligible":False,"ranking_eligible":False}
def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 primary-evidence","Accept":"text/html"})
 with urlopen(req,timeout=30) as response:
  if response.geturl()!=URL or "html" not in response.headers.get("Content-Type","").lower():
   raise ValueError("Wrong SGX original response")
  raw=response.read(3_000_001)
 if len(raw)>3_000_000:raise ValueError("Source oversized")
 return raw
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();out={"schema_version":"sgx-ocbc-q3-original-probe-v143",
  "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:out["record"]=parse(fetch());out["status"]="SGX_OCBC_2026Q3_PRIMARY_ANNOUNCEMENT_VERIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:250]
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
