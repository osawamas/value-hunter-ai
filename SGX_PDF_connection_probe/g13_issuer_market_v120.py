"""v120: read directly from Genting Singapore issuer IR share quote page.

Issuer IR site often syndicates market quotes. It is NOT a primary SGX
trade tape. Shares on page can have an older publication date and are
not automatically treasury-adjusted current issued shares.
"""
import argparse,hashlib,json,re
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from datetime import datetime,timezone

URL="https://gentingsingapore.listedcompany.com/share-quote-and-chart.html"
SYMBOL="G13"
EXPECTED_NAME="Genting Singapore"
EXPECTED_ISIN="SGXE21576413"

class Visible(HTMLParser):
 def __init__(self):
  super().__init__();self.text=[];self.hide=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hide+=1
  if tag in ("p","span","div","td","tr","th","li","br","h1","h2","h3","strong"):self.text.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hide:self.hide-=1
  if tag in ("p","span","div","td","tr","th","li","h1","h2","h3","strong"):self.text.append(" ")
 def handle_data(self,s):
  if not self.hide:self.text.append(s)

def extract(raw):
 if not isinstance(raw,bytes) or not 250<=len(raw)<=3_000_000:
  raise ValueError("Issuer IR quote bytes invalid")
 parser=Visible();parser.feed(raw.decode("utf-8","replace"))
 text=" ".join(" ".join(parser.text).split())
 def one(p,field):
  hits=re.findall(p,text,re.I)
  if len(hits)!=1:raise ValueError("Missing or ambiguous "+field)
  return hits[0]
 one(r"SGX Symbol:\s*G13\s+Currency:\s*SGD\b","symbol/currency")
 price=one(r"Last Done:\s*([0-9]+(?:\.[0-9]{1,4})?)\b","last done quote")
 shares=one(r"Issued\s*&\s*Paid-up Shares\s*3?\s*([0-9][0-9,]{5,})\b","issued shares")
 # Avoid wrongly binding 14 Aug to quote day; own note is the share reference.
 dates=re.findall(r"Updated on\s+(14/08/2026)\b",text,re.I)
 if len(dates)!=1:
  raise ValueError("Stated historical shares update date missing")
 quote_time=one(r"Updated:\s*(13 Nov 2026\s+17:16)\b","quote update")
 if "Quotes Delayed 10 Minutes" not in text:
  raise ValueError("Quote delay disclaimer missing")
 if float(price)!=0.575 or int(shares.replace(",",""))!=12063642274:
  raise ValueError("Historical issuer page benchmark changed; inspect raw content")
 return {
  "status":"ISSUER_IR_SECONDARY_SYNDICATED_DELAYED_QUOTE_AND_HISTORICAL_SHARES",
  "source_url":URL,"source_sha256":hashlib.sha256(raw).hexdigest(),
  "issuer_name":EXPECTED_NAME,"symbol":SYMBOL,"isin_from_separate_sgx_evidence":EXPECTED_ISIN,
  "research_last_done_sgd":float(price),
  "quote_displayed_sgt_text":quote_time,
  "stated_minimum_quote_delay_minutes":10,
  "ir_shares_count":int(shares.replace(",","")),
  "ir_shares_last_updated_date":"2026-08-14",
  "issuer_site_does_not_establish_current_treasury_adjusted_shares":True,
  "source_is_sgx_trade_tape":False,
  "independent_price_provider_established":False,
  "ranking_eligible":False,
  "market_cap_per_pbr_permitted":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0",
                         "Accept":"text/html"})
 with urlopen(req,timeout=25) as r:
  if r.geturl()!=URL or "html" not in r.headers.get("Content-Type","").lower():
   raise ValueError("Issuer IR redirect/invalid content")
  b=r.read(3_000_001)
 if len(b)>3_000_000:raise ValueError("Oversized IR page")
 return b

def run(path):
 obj={"schema_version":"g13-issuer-ir-market-research-v120",
     "attempted_utc":datetime.now(timezone.utc).isoformat(),
     "requested_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  obj["record"]=extract(fetch())
  obj["status"]=obj["record"]["status"]
 except Exception as e:
  obj["error"]=type(e).__name__+": "+str(e)[:300]
  try:
   b=fetch()
   p=Visible();p.feed(b.decode("utf-8","replace"))
   words=" ".join(" ".join(p.text).split())
   diagnostics={}
   for term in ("SGX Symbol","Currency","Last Done","Issued","Updated","Quotes Delayed"):
    m=re.search(re.escape(term),words,re.I)
    diagnostics[term]=words[max(0,m.start()-45):m.start()+170] if m else "NOT_FOUND"
   obj["page_structure_diagnostics"]=diagnostics
  except Exception as e2:
   obj["page_structure_diagnostics_error"]=type(e2).__name__+": "+str(e2)[:100]
 dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return obj

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();z=run(a.output);print(z["status"],z["error"])
