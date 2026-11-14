"""v119: Genting Singapore G13 historical SGX primary identity link.

Confirms issuer + ticker + ISIN in the same official SGX announcement.
Historical source is not a current share-count or price verification.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://links.sgx.com/1.0.0/corporate-announcements/NF6GZEGGD4XBFOVY/"
ISSUER="GENTING SINGAPORE LIMITED"
ISIN="SGXE21576413"
TICKER="G13"
REFERENCE="SG260130OTHRZ1XN"
BROADCAST="30-Jan-2026 17:20:38"

class Visible(HTMLParser):
 def __init__(self):
  super().__init__();self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hidden+=1
  if tag in ("div","p","span","td","tr","h1","h2","h3","li","br"):self.parts.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hidden:self.hidden-=1
  if tag in ("div","p","span","td","tr","h1","h2","h3","li"):self.parts.append(" ")
 def handle_data(self,v):
  if not self.hidden:self.parts.append(v)

def parse(raw):
 if not isinstance(raw,bytes) or not 200<=len(raw)<=3_000_000:
  raise ValueError("Invalid official announcement response")
 p=Visible();p.feed(raw.decode("utf-8","replace"))
 s=" ".join(" ".join(p.parts).split())
 binding=(r"Issuer\s*/\s*Manager\s+"+re.escape(ISSUER)+
          r"\s+Securit(?:y|ies)\s+"+re.escape(ISSUER)+
          r"\s*-\s*"+ISIN+r"\s*-\s*"+TICKER+r"\b")
 if len(re.findall(binding,s,re.I))!=1:
  raise ValueError("Missing unique official issuer-ISIN-ticker match")
 if len(re.findall(re.escape(ISSUER)+r"\s*-\s*"+ISIN+r"\s*-\s*"+TICKER+r"\b",s,re.I))!=1:
  raise ValueError("Duplicated or ambiguous security identity")
 if len(re.findall(r"Announcement Reference\s+"+REFERENCE+r"\b",s,re.I))!=1:
  raise ValueError("Announcement reference missing or ambiguous")
 if len(re.findall(r"Date\s*&\s*Time of Broadcast\s+"+re.escape(BROADCAST)+r"\b",s,re.I))!=1:
  raise ValueError("Announcement broadcast time missing or ambiguous")
 return {"status":"SGX_PRIMARY_HISTORICAL_G13_TICKER_ISIN_LINK",
   "issuer":ISSUER,"symbol":TICKER,"isin":ISIN,"reference":REFERENCE,
   "broadcast_sgt_text":BROADCAST,"source_url":URL,
   "original_html_sha256":hashlib.sha256(raw).hexdigest(),
   "historical_issuer_identity_only":True,
   "issuer_current_listing_status_verified":False,
   "current_shares_verified":False,"current_quote_verified":False,
   "financial_independence_verified":False,
   "market_cap_per_pbr_use_permitted":False,
   "ranking_eligible":False}

def fetch():
 req=Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 primary-evidence-research",
                          "Accept":"text/html"})
 with urlopen(req,timeout=25) as r:
  if r.geturl()!=URL:raise ValueError("Unexpected SGX redirect")
  if "html" not in r.headers.get("Content-Type","").lower():
   raise ValueError("SGX original not HTML")
  raw=r.read(3_000_001)
 if len(raw)>3_000_000:raise ValueError("SGX original oversized")
 return raw

def run(output):
 z={"schema_version":"sgx-g13-primary-identity-v119",
    "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
    "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  z["record"]=parse(fetch());z["status"]=z["record"]["status"]
 except Exception as e:
  z["error"]=type(e).__name__+": "+str(e)[:280]
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(z,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return z

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();r=run(a.output);print(r["status"],r["error"])
