"""v163: probe issuer-hosted UOB 2026-11-13 announcement publication.

The landing page is UOB's corporate IR host. A UOB-hosted reproduction
does NOT alone prove the SGX original announcement or the current share count.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen

URL="https://uob.listedcompany.com/sgx-announcements/news.html?id=2634252"
HOMEPAGE="https://uob.listedcompany.com/"
REFERENCE="SG261113OTHRHOAF"

class Reader(HTMLParser):
 def __init__(self):super().__init__();self.words=[];self.links=[];self.link=None;self.hidden=0
 def handle_starttag(self,tag,attrs):
  x=dict(attrs)
  if tag in ("script","style"):self.hidden+=1
  if tag=="a":self.link={"href":x.get("href",""),"text":[]}
  if tag in ("p","div","td","tr","h1","h2","span","br"):self.words.append(" ")
 def handle_data(self,value):
  if not self.hidden:self.words.append(value)
  if self.link is not None:self.link["text"].append(value)
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hidden:self.hidden-=1
  if tag=="a" and self.link is not None:self.links.append(self.link);self.link=None

def analyze(raw):
 if not isinstance(raw,bytes) or not 100<len(raw)<4_000_000:raise ValueError("Invalid issuer IR HTML")
 p=Reader();p.feed(raw.decode("utf-8","replace"))
 visible=" ".join(" ".join(p.words).split())
 has_reference=REFERENCE in visible
 has_title=bool(re.search(r"(?:Daily Share Buy-Back Notice|Share Buy Back)",visible,re.I))
 has_date=bool(re.search(r"(?:13\s+Nov(?:ember)?\s+2026|Nov\s+13,\s+2026|13/11/2026)",visible,re.I))
 links=[]
 for a in p.links:
  href=a["href"].strip()
  if not href:continue
  full=urljoin(URL,href)
  u=urlparse(full)
  if u.scheme=="https" and u.hostname in ("uob.listedcompany.com","links.sgx.com"):
   if ("sgx" in full.lower() or "pdf" in full.lower() or "buy" in " ".join(a["text"]).lower()):
    links.append({"url":full[:400],"label":" ".join(" ".join(a["text"]).split())[:100]})
 return {"schema_version":"uob-ir-nov13-page-evidence-v163",
  "page_url":URL,"response_html_sha256":hashlib.sha256(raw).hexdigest(),
  "response_bytes":len(raw),"visible_chars":len(visible),
  "expected_announcement_ref_visible":has_reference,
  "buyback_title_visible":has_title,
  "date_nov13_visible":has_date,
  "UOB_ir_announcement_identity_verified":bool(has_reference and has_title and has_date),
  "candidate_public_ir_or_sgx_links":links[:35],
  "sgx_original_announcement_verified":False,
  "uob_treasury_adjusted_shares_from_primary_sgx":None,
  "latest_outstanding_shares_verified":False,
  "ranking_eligible":False}

def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 primary-source-discovery",
                           "Accept":"text/html"})
 with urlopen(req,timeout=25) as res:
  dest=urlparse(res.geturl())
  if dest.scheme!="https" or dest.hostname!="uob.listedcompany.com":
   raise ValueError("Unexpected IR site redirect")
  if "html" not in res.headers.get("Content-Type","").lower():
   raise ValueError("UOB IR did not serve HTML")
  raw=res.read(4_000_001)
 return raw

def main():
 a=argparse.ArgumentParser();a.add_argument("--output",required=True)
 options=a.parse_args()
 out={"schema_version":"uob-ir-2026-11-13-probe-v163",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":"NOT_RETRIEVED","record":None,"error":None}
 try:
  out["record"]=analyze(fetch())
  out["status"]="UOB_ISSUER_IR_PAGE_PARSED_IDENTITY_NOT_VERIFIED"
  if out["record"]["UOB_ir_announcement_identity_verified"]:
   out["status"]="UOB_NOV13_ISSUER_IR_ANNOUNCEMENT_IDENTIFIED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:250]
 target=Path(options.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
