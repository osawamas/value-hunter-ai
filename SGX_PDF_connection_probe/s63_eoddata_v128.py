"""v128: S63 official-market-date historical quote corroboration from EODData.

Second *website* only, not verified upstream independence or SGX trade tape.
The purpose is to audit 13-Nov quote and OHLC/volume without promotion.
"""
import argparse,hashlib,json,re
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from datetime import datetime,timezone

URL="https://www.eoddata.com/stockquote/SGX/S63.htm"
DATE="13 Nov 2026"

class Visible(HTMLParser):
 def __init__(self):
  super().__init__();self.parts=[];self.hide=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hide+=1
  if tag in ("p","div","span","td","tr","th","h1","h2","h3","li","br","strong"):
   self.parts.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hide:self.hide-=1
  if tag in ("p","div","span","td","tr","th","h1","h2","h3","li","strong"):
   self.parts.append(" ")
 def handle_data(self,val):
  if not self.hide:self.parts.append(val)

def parse(raw):
 if not isinstance(raw,bytes) or not 100<len(raw)<3_000_000:
  raise ValueError("Invalid secondary page")
 parser=Visible();parser.feed(raw.decode("utf-8","replace"))
 text=" ".join(" ".join(parser.parts).split())
 if not re.search(r"SGX,\s*S63\s*:\s*ST Engineering",text,re.I):
  raise ValueError("Market ticker or issuer not present")
 # Require the date, LAST and 13-Nov close in the same source
 if not re.search(r"\b13 Nov 2026\b",text,re.I):
  raise ValueError("Expected historical trade date not found")
 prices=re.findall(r"\bLAST:\s*(9\.670)\b",text,re.I)
 if len(prices)!=1:
  raise ValueError("Unique S63 LAST not identified")
 # Historical table row must belong to actual date, distinct from LAST panel.
 rows=re.findall(r"\b13 Nov 26\b\s+(9\.660)\s+(9\.770)\s+(9\.470)\s+(9\.670)\s+([0-9.]+M|[0-9,]+)",text,re.I)
 if len(rows)!=1:
  raise ValueError("Historical daily OHLC row missing or ambiguous")
 opening,high,low,close,volume=rows[0]
 if not float(low)<=float(close)<=float(high):
  raise ValueError("OHLC range invalid")
 return {
  "status":"SECONDARY_EODDATA_S63_HISTORICAL_CLOSE_MATCHED",
  "symbol":"S63","trade_date_sgt":"2026-11-13","currency":"SGD",
  "source_url":URL,"source_html_sha256":hashlib.sha256(raw).hexdigest(),
  "close_sgd_research":float(close),"open_sgd":float(opening),
  "high_sgd":float(high),"low_sgd":float(low),
  "published_volume_text":volume,
  "different_website_from_yahoo":True,
  "upstream_market_data_independence_verified":False,
  "original_sgx_exchange_trade_tape_verified":False,
  "exact_executed_trade_time_verified":False,
  "eligible_for_market_cap_per_pbr":False,"ranking_eligible":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI historical-research)",
                         "Accept":"text/html"})
 with urlopen(req,timeout=25) as response:
  if response.geturl()!=URL:raise ValueError("Unexpected redirected source")
  if "html" not in response.headers.get("Content-Type","").lower():
   raise ValueError("Not HTML")
  raw=response.read(3_000_001)
 if len(raw)>3_000_000:raise ValueError("Secondary page too large")
 return raw

def run(output):
 obj={"schema_version":"sgx-s63-second-site-price-v128",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "requested_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  obj["record"]=parse(fetch())
  obj["status"]=obj["record"]["status"]
 except Exception as exc:
  obj["error"]=type(exc).__name__+": "+str(exc)[:250]
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return obj

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();x=run(a.output)
 print(x["status"],x["error"])
