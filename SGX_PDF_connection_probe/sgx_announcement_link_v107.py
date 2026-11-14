"""v107: independently validate an SGX-hosted issuer / ISIN / ticker linkage.

Only a single known SGX announcement; no universe completeness, valuation
or live quote claims.
"""
import argparse,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone

URL="https://links.sgx.com/1.0.0/corporate-announcements/U6RBLH1JFNDV1QZT/4d07e8c30959620ceca55f7e574d69cf8270329fdcd719a5a2992624f3474f80"
NAME="DBS GROUP HOLDINGS LTD"
ISIN="SG1L01001701"
CODE="D05"
REF="SG260309OTHROF8R"

class Extract(HTMLParser):
 def __init__(self):
  super().__init__();self.text=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("style","script"):self.hidden+=1
  if tag in ("div","p","h1","h2","h3","span","tr","td","br","li"):self.text.append(" ")
 def handle_endtag(self,tag):
  if tag in ("style","script") and self.hidden:self.hidden-=1
  if tag in ("div","p","h1","h2","h3","span","tr","td","li"):self.text.append(" ")
 def handle_data(self,data):
  if not self.hidden:self.text.append(data)

def parse(raw):
 if not isinstance(raw,bytes) or not 200<=len(raw)<=3_000_000:
  raise ValueError("SGX announcement content invalid")
 h=Extract();h.feed(raw.decode("utf-8","replace"))
 plain=" ".join(" ".join(h.text).split())
 pattern=r"Issuer\s*/\s*Manager\s+"+NAME+r"\s+Securit(?:y|ies)\s+"+NAME+r"\s*-\s*"+ISIN+r"\s*-\s*"+CODE+r"\b"
 if len(re.findall(pattern,plain,re.I))!=1:
  raise ValueError("No unique issuer-ISIN-counter binding in primary announcement")
 if len(re.findall(re.escape(NAME)+r"\\s*-\\s*"+ISIN+r"\\s*-\\s*"+CODE+r"\\b",plain,re.I)) != 1:
  raise ValueError("Duplicate issuer-ISIN-counter references")
 if len(re.findall(r"Announcement Reference\s+"+REF+r"\b",plain,re.I))!=1:
  raise ValueError("Announcement reference wrong or ambiguous")
 if not re.search(r"Date\s*&\s*Time of Broadcast\s+09-Mar-2026\s+07:33:28\b",plain,re.I):
  raise ValueError("Filing broadcast timestamp mismatch")
 return {"status":"SGX_PRIMARY_ANNOUNCEMENT_COUNTER_ISIN_LINK_MATCHED",
         "source_url":URL,"source_html_sha256":hashlib.sha256(raw).hexdigest(),
         "issuer":NAME,"symbol":CODE,"isin":ISIN,
         "announcement_reference":REF,"announcement_broadcast_sgt_text":"09-Mar-2026 07:33:28",
         "single_historical_announcement_only":True,
         "issuer_active_as_of_now_verified":False,
         "official_entire_sgx_master_verified":False,
         "financial_values_verified_by_this_evidence":False,
         "ranking_eligible":False}

def fetch():
 with urlopen(Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research","Accept":"text/html"}),timeout=25) as resp:
  if resp.geturl()!=URL:raise ValueError("Untrusted SGX redirect")
  if "html" not in resp.headers.get("Content-Type","").lower():
   raise ValueError("Not official HTML")
  data=resp.read(3_000_001)
 if len(data)>3_000_000:raise ValueError("Oversized")
 return data

def run(output,raw=None):
 out={"schema_version":"sgx-announcement-counter-link-v107",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=parse(fetch() if raw is None else raw)
  out["status"]=out["record"]["status"]
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:300]
 p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return out

if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",required=True)
 x=a.parse_args();r=run(x.output);print(r["status"],r["error"])
