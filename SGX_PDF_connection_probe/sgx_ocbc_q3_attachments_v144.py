"""v144: discover true OCBC 3Q SGX attachment URLs, fail-closed.

No guessing FileIDs, no interpretation of bank financials from landing HTML.
"""
import argparse,hashlib,json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from sgx_ocbc_q3_original_v143 import URL,ATTACHMENTS,fetch

class Anchors(HTMLParser):
 def __init__(self):super().__init__();self.anchors=[];self.current=None
 def handle_starttag(self,tag,attrs):
  if tag=="a":self.current={"attrs":dict(attrs),"texts":[]}
 def handle_data(self,data):
  if self.current is not None:self.current["texts"].append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.current is not None:
   self.anchors.append(self.current);self.current=None

def discover(raw,manifest):
 if (manifest.get("status")!="SGX_OCBC_2026Q3_PRIMARY_ANNOUNCEMENT_VERIFIED" or
     manifest.get("record",{}).get("source_html_sha256")!=hashlib.sha256(raw).hexdigest() or
     manifest["record"].get("symbol")!="O39"):
  raise ValueError("No authenticated official announcement HTML")
 p=Anchors();p.feed(raw.decode("utf-8","replace"))
 output=[]
 for name in ATTACHMENTS:
  links=[]
  for a in p.anchors:
   label=" ".join(" ".join(a["texts"]).split())
   href=a["attrs"].get("href","")
   if name not in (label,href.split("/")[-1]):continue
   resolved=urljoin(URL,href)
   parsed=urlparse(resolved)
   if (parsed.scheme=="https" and parsed.hostname=="links.sgx.com"
       and not parsed.username and not parsed.password
       and (parsed.path.startswith("/FileOpen/") or
            parsed.path.startswith("/1.0.0/corporate-announcements/"))):
    links.append(resolved)
  links=sorted(set(links))
  output.append({"filename":name,"resolved_official_link":links[0] if len(links)==1 else None,
                 "unique_direct_sgx_link":len(links)==1})
 return {"schema_version":"sgx-ocbc-q3-official-attachment-links-v144",
    "original_announcement_url":URL,
    "source_html_sha256":hashlib.sha256(raw).hexdigest(),
    "official_attachment_url_count":sum(x["unique_direct_sgx_link"] for x in output),
    "all_three_verified_attachment_links":all(x["unique_direct_sgx_link"] for x in output),
    "downloaded_original_pdfs":False,
    "quarterly_metrics_extracted":False,
    "current_market_data_verified":False,
    "ranking_eligible":False,"attachments":output}

def main():
 p=argparse.ArgumentParser();p.add_argument("--manifest",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 m=json.loads(Path(a.manifest).read_text())
 o={"schema_version":"sgx-ocbc-q3-attachment-probe-v144","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  o["record"]=discover(fetch(),m)
  o["status"]="SGX_OCBC_Q3_ATTACHMENT_LINKS_RESEARCHED"
 except Exception as e:o["error"]=type(e).__name__+": "+str(e)[:250]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(o["status"],o["error"],o["record"] and o["record"]["official_attachment_url_count"])
if __name__=="__main__":main()
