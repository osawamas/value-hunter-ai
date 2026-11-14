"""v97: discover SGX symbol candidates from a secondary alphabetical directory.

The SGinvestors alphabetical page is a SECONDARY directory, not SGX's
authoritative list, not guaranteed complete or updated. Candidate tickers
must not automatically join verified finance, market caps or investment rank.
Requires raw page provenance SHA256, unique ticker, and known 7 symbol audit.
"""
import argparse,hashlib,json,re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://sginvestors.io/sgx/stock-listing/alpha"
KNOWN=("S68","G13","S20","S63","D05","O39","U11")
CODE=re.compile(r"^(.+?)\s*\(SGX:\s*([A-Z0-9]{1,6})\)\s*$",re.I)

class AnchorText(HTMLParser):
 def __init__(self):
  super().__init__();self.depth=0;self.content=[];self.anchors=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   self.depth=1;self.content=[]
  elif self.depth:self.depth+=1
 def handle_endtag(self,tag):
  if self.depth:
   self.depth-=1
   if not self.depth:
    label=" ".join(" ".join(self.content).split())
    self.anchors.append(label)
    self.content=[]
 def handle_data(self,data):
  if self.depth:self.content.append(data)

def parse(raw):
 if not isinstance(raw,bytes) or not 100<=len(raw)<=6_000_000:
  raise ValueError("SGX directory HTML invalid")
 html=unescape(raw.decode("utf-8","replace"))
 if not re.search(r"SGX Listed Companies|SGX Stocks|SGX Listed Stock",html,re.I):
  raise ValueError("Directory title absent")
 h=AnchorText();h.feed(html)
 result={}
 duplicates=[]
 for label in h.anchors:
  match=CODE.fullmatch(label)
  if match is None:continue
  name,code=match.groups()
  code=code.upper()
  if len(name)<3 or not re.search(r"[A-Z]",name.upper()):
   raise ValueError("Directory symbol has no name")
  if code in result:
   duplicates.append({"symbol":code,"previous":result[code],"new":name})
   continue
  result[code]=name
 if not 100<=len(result)<=1200:
  raise ValueError("SGX candidate directory too sparse or excessive")
 missing=sorted(set(KNOWN)-set(result))
 if missing:
  raise ValueError("Missing already-known SGX issuers: "+",".join(missing))
 if duplicates:
  raise ValueError("Duplicate SGX ticker candidates: "+str(duplicates[:3]))
 return {
  "status":"SECONDARY_SGX_UNIVERSE_CANDIDATES_DIAGNOSTIC_ONLY",
  "source_url":URL,
  "raw_html_sha256":hashlib.sha256(raw).hexdigest(),
  "candidate_count":len(result),
  "known_7_present":True,
  "stock_tickers":[{"symbol":sym,"display_name":name}
                   for sym,name in sorted(result.items())],
  "candidate_not_verified_issuer_registry":True,
  "company_security_type_not_independently_verified":True,
  "inactive_or_delisted_not_independently_screened":True,
  "authoritative_sgx_listing_completeness_unverified":True,
  "current_price_verified":False,
  "ranking_eligible":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only",
                          "Accept":"text/html"})
 with urlopen(req,timeout=25) as resp:
  if resp.geturl()!=URL:raise ValueError("SGX secondary directory redirected")
  raw=resp.read(6_000_001)
 if len(raw)>6_000_000:raise ValueError("SGX secondary directory too large")
 return raw

def run(output,raw=None):
 result={"status":"NOT_VERIFIED","source_url":URL,"record":None,"error":None}
 try:
  data=fetch() if raw is None else raw
  result["record"]=parse(data)
  result["status"]=result["record"]["status"]
 except Exception as exc:
  result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return result

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 args=p.parse_args()
 result=run(args.output)
 print("SGX universe",result["status"],result["record"]["candidate_count"] if result["record"] else result["error"])
 raise SystemExit(0 if result["record"] is not None else 1)
