"""v96: inspect timestamped SGinvestors SGX bank quote pages, research only.

This is not an exchange-authoritative real-time price feed. Attempts to
parse a single identified SGX ticker/currency/SGT datetime quote from the
visible issuer stock-info page. On 403, layout drift, stale or ambiguous
results: fail closed, never populate price_sgd or market-cap/PE/PB.
"""
import argparse,hashlib,json,re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

SOURCES={
 "D05":{"url":"https://sginvestors.io/sgx/stock/d05-dbs/stock-info",
        "identity":"DBS GROUP HOLDINGS LTD","isin":"SG1L01001701"},
 "O39":{"url":"https://sginvestors.io/sgx/stock/o39-ocbc-bank/stock-info",
        "identity":"OVERSEA-CHINESE BANKING CORP","isin":"SG1S04926220"},
 "U11":{"url":"https://sginvestors.io/sgx/stock/u11-uob/stock-info",
        "identity":"UNITED OVERSEAS BANK LTD","isin":"SG1M31001969"},
}
STATUS="SECONDARY_TIMESTAMPED_SGX_BANK_QUOTE_DIAGNOSTIC_ONLY"

class VisibleText(HTMLParser):
 def __init__(self):
  super().__init__();self.out=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hidden+=1
  if tag in ("p","div","span","td","h1","h2","h3","br","li"):self.out.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hidden:self.hidden-=1
  if tag in ("p","div","span","td","h1","h2","h3","li"):self.out.append(" ")
 def handle_data(self,data):
  if not self.hidden:self.out.append(data)

def parse(symbol,raw):
 if symbol not in SOURCES or not isinstance(raw,bytes) or len(raw)>5_000_000:
  raise ValueError("Unknown SGX quote source/size")
 doc=VisibleText();doc.feed(raw.decode("utf-8","replace"))
 plain=" ".join(unescape(" ".join(doc.out)).split())
 expected=SOURCES[symbol]
 if (expected["identity"].lower() not in plain.lower()
     or expected["isin"] not in plain
     or "SGX:"+symbol not in plain):
  raise ValueError("SGX bank identity/ticker/ISIN not verified")
 # Reject a page with multiple contradictory summary-price/time pairs.
 hits=re.findall(
  r"SGD\s*(\d{1,3}\.\d{3})\s*[-+−]?\s*[\d.,()%\s/-]{0,100}"
  r"Share Price as of:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})",
  plain,flags=re.I)
 if len(hits)!=1:
  raise ValueError("Secondary SGX quote block missing or ambiguous")
 rawprice,day,time=hits[0]
 dt=datetime.strptime(day+" "+time,"%Y-%m-%d %H:%M")
 if dt.strftime("%Y-%m-%d")!=day or day>"2026-11-14":
  raise ValueError("SGX quote as-of day invalid or in future")
 price=float(rawprice)
 if not (0.01<=price<=10000):
  raise ValueError("SGD quote outside bounds")
 return {"symbol":symbol,"status":STATUS,
   "quote_price_sgd":price,"quote_as_of_local":dt.isoformat(timespec="minutes")+"+08:00",
   "quote_timezone":"Asia/Singapore",
   "quote_source_url":expected["url"],
   "quote_html_sha256":hashlib.sha256(raw).hexdigest(),
   "source_kind":"SECONDARY_THIRD_PARTY_STOCK_INFO",
   "quote_delay_not_verified":True,
   "sgx_primary_market_tick_not_verified":True,
   "usable_for_current_market_cap":False,
   "usable_for_per_pbr":False,"ranking_eligible":False}

def fetch(symbol):
 url=SOURCES[symbol]["url"]
 req=Request(url,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only",
                          "Accept":"text/html"})
 with urlopen(req,timeout=25) as response:
  if response.geturl()!=url:
   raise ValueError("Third-party quote redirect rejected")
  data=response.read(5_000_001)
 if len(data)>5_000_000:raise ValueError("Quote page too large")
 return data

def run(symbol,output,raw=None):
 result={"symbol":symbol,"status":"NOT_VERIFIED",
         "source_url":SOURCES[symbol]["url"],"record":None,"error":None}
 try:
  data=fetch(symbol) if raw is None else raw
  item=parse(symbol,data)
  result["record"]=item;result["status"]=item["status"]
 except Exception as exc:
  result["error"]=f"{type(exc).__name__}: {str(exc)[:280]}"
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return result

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--symbol",choices=tuple(SOURCES),required=True)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 result=run(a.symbol,a.output)
 print(a.symbol,result["status"],result["error"])
 raise SystemExit(0 if result["record"] is not None else 1)
