"""v94: UOB issuer investor-relations quote source diagnostic, not valuation.

Issuer-linked investor information may show 'last done' and a timestamp.
It is NOT guaranteed to be live, consolidated SGX last trade or official
exchange market data. Keep in research-only evidence until separately
validated alongside shares and the market data feed.
"""
import argparse,hashlib,json,re
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://uob.listedcompany.com/"
REFERENCE_LAST="37.750"
REFERENCE_DATE="2026-11-13"
REFERENCE_TIME="17:14"
PATTERNS=(
  (re.compile(r'["\\\']last_done["\\\']\s*:\s*["\\\'](?P<price>[\d,.]+)["\\\']',re.I),
   re.compile(r'["\\\']datetime["\\\']\s*:\s*["\\\'](?P<timestamp>[^"\\\']+)["\\\']',re.I)),
  (re.compile(r'Last\s+Done\s*[:]?\s*(?P<price>\d+\.\d{2,4})',re.I),
   re.compile(r'(?P<timestamp>13\s+Nov\s+2026\s+17:14)',re.I)),
)

def parse(url,raw):
 if url!=URL or not isinstance(raw,bytes) or len(raw)>2_000_000:
  raise ValueError("Unrecognized issuer IR quote origin or page size")
 html=unescape(raw.decode("utf-8","replace"))
 if "UOB" not in html.upper() or "quote" not in html.lower():
  raise ValueError("UOB issuer investor page or quote block absent; bytes="+str(len(raw))+"; has_last_done="+str("last_done" in html)+"; has_uob="+str("UOB" in html.upper())+"; prefix="+re.sub(r"[^\\x20-\\x7E]"," ",html[:180]))
 fields=[]
 for price_rx,time_rx in PATTERNS:
  prices=[x.group("price") for x in price_rx.finditer(html)]
  stamps=[x.group("timestamp") for x in time_rx.finditer(html)]
  if len(prices)==1 and len(stamps)==1:
   fields.append((prices[0],stamps[0]))
 if not fields:
  raise ValueError("IR last-done price and timestamp missing or ambiguous")
 if len(set(fields))!=1:
  raise ValueError("UOB quoted price/time not consistent across page layouts")
 rawprice,stamp=fields[0]
 if not re.fullmatch(r"\d{1,3}\.\d{3}",rawprice):
  raise ValueError("Price formatting or currency units ambiguous")
 if not re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}",stamp):
  raise ValueError("Ambiguous quote local date and time")
 d=datetime.strptime(" ".join(stamp.split()),"%d %b %Y %H:%M")
 if d.strftime("%Y-%m-%d")!=REFERENCE_DATE or d.strftime("%H:%M")!=REFERENCE_TIME:
  raise ValueError("Historical regression quote timestamp changed")
 if rawprice!=REFERENCE_LAST:
  raise ValueError("IR quote changed; requires fresh timestamp verification")
 return {
  "symbol":"U11","status":"ISSUER_IR_LAST_DONE_RESEARCH_SNAPSHOT_NOT_SGX_PRIMARY_QUOTE",
  "source_url":url,"source_html_sha256":hashlib.sha256(raw).hexdigest(),
  "price_sgd_reference":float(rawprice),
  "quote_as_of_local":d.isoformat(timespec="minutes")+"+08:00",
  "timezone":"Asia/Singapore",
  "source_kind":"ISSUER_IR_DISPLAY_VIA_LISTEDCOMPANY",
  "price_type":"LAST_DONE_AS_DISPLAYED_BY_IR",
  "exchange_trade_tick_independently_verified":False,
  "delayed_or_realtime_feed_class_not_verified":True,
  "stale_without_new_document_refresh":True,
  "eligible_for_live_market_cap":False,"eligible_for_per_pbr":False,
  "ranking_eligible":False
 }

def fetch():
 request=Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only",
                              "Accept":"text/html"})
 with urlopen(request,timeout=25) as response:
  if response.geturl()!=URL:raise ValueError("Issuer IR page redirected")
  raw=response.read(2_000_001)
 if len(raw)>2_000_000:raise ValueError("UOB IR page too large")
 return raw

def run(output,raw=None):
 result={"symbol":"U11","status":"NOT_VERIFIED","source_url":URL,"record":None,"error":None}
 try:
  data=fetch() if raw is None else raw
  record=parse(URL,data)
  result["record"]=record
  result["status"]=record["status"]
 except Exception as exc:
  result["error"]=f"{type(exc).__name__}: {str(exc)[:320]}"
 target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return result

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
 result=run(a.output)
 print(result["status"],result["error"])
 raise SystemExit(0 if result["record"] is not None else 1)
