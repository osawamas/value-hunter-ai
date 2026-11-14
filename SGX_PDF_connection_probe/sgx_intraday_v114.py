"""v114: observed intraday 5-minute SGX ticker chart bars from Yahoo, secondary research.

This does NOT verify last execution time on SGX. The bar timestamp is
the interval timestamp supplied by Yahoo, not proof of trade execution.
"""
import argparse,hashlib,json,math
from pathlib import Path
from datetime import datetime,timedelta,timezone,time
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

SGT=ZoneInfo("Asia/Singapore")
TICKERS={"D05":"D05.SI","O39":"O39.SI","U11":"U11.SI"}
BASE="https://query1.finance.yahoo.com/v8/finance/chart/"
SUFFIX="?interval=5m&range=5d"

def parse(symbol,raw,now=None):
 if symbol not in TICKERS or not isinstance(raw,bytes) or not 50<len(raw)<=3_000_000:
  raise ValueError("Invalid body or counter")
 data=json.loads(raw)
 chart=data.get("chart",{}) if isinstance(data,dict) else {}
 if not isinstance(chart,dict) or chart.get("error") is not None:
  raise ValueError("Chart denied or invalid")
 results=chart.get("result")
 if not isinstance(results,list) or len(results)!=1:
  raise ValueError("No unique chart")
 x=results[0];meta=x.get("meta") or {}
 if (meta.get("symbol")!=TICKERS[symbol] or meta.get("currency")!="SGD" or
     meta.get("exchangeTimezoneName")!="Asia/Singapore" or
     meta.get("instrumentType")!="EQUITY"):
  raise ValueError("Symbol/currency/market metadata disagree")
 bars=x.get("timestamp");listq=x.get("indicators",{}).get("quote")
 if (not isinstance(bars,list) or not 1<=len(bars)<=1200 or
     not isinstance(listq,list) or len(listq)!=1 or not isinstance(listq[0],dict)):
  raise ValueError("Invalid intraday bars")
 close=listq[0].get("close")
 if (not isinstance(close,list) or len(close)!=len(bars) or
     any(type(t) is not int or t<=0 for t in bars) or
     bars!=sorted(set(bars))):
  raise ValueError("Bar ordering, duplication or price alignment invalid")
 ref=now or datetime.now(timezone.utc)
 if ref.tzinfo is None:raise ValueError("Retrieval date must be aware")
 valid=[]
 for timestamp,price in zip(bars,close):
  if price is None:continue
  if type(price) not in (int,float) or not math.isfinite(price) or not 0<price<10000:
   raise ValueError("Bad price in intraday bar")
  dt=datetime.fromtimestamp(timestamp,timezone.utc)
  if dt>ref+timedelta(minutes=5):
   raise ValueError("Future intraday bar")
  local=dt.astimezone(SGT)
  # Only retain regular SGX daytime bar windows conservatively.
  if local.weekday()<5 and time(9,0)<=local.time()<=time(17,10):
   valid.append((dt,float(price)))
 if not valid:raise ValueError("No valid regular session bars")
 dt,price=valid[-1]
 if ref-dt>timedelta(days=7):
  raise ValueError("Last bar too stale")
 return {
   "status":"YAHOO_SGX_INTRADAY_BAR_RESEARCH_ONLY",
   "symbol":symbol,"provider_symbol":TICKERS[symbol],
   "source_url":BASE+TICKERS[symbol]+SUFFIX,
   "response_sha256":hashlib.sha256(raw).hexdigest(),
   "bar_count_total":len(bars),"regular_session_bars":len(valid),
   "last_bar_timestamp_utc":dt.isoformat(),
   "last_bar_date_sgt":dt.astimezone(SGT).date().isoformat(),
   "last_bar_price_sgd":round(price,6),
   "provider_bar_interval_minutes":5,
   "bar_timestamp_is_verified_trade_time":False,
   "price_independently_exchange_confirmed":False,
   "acceptable_as_realtime_quote":False,
   "eligible_for_market_cap_per_pbr":False,
   "ranking_eligible":False
 }

def fetch(symbol):
 url=BASE+TICKERS[symbol]+SUFFIX
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0",
                          "Accept":"application/json"})
 with urlopen(req,timeout=25) as resp:
  if resp.geturl()!=url:raise ValueError("Quote redirect")
  if "json" not in resp.headers.get("Content-Type","").lower():
   raise ValueError("Non-JSON body")
  body=resp.read(3_000_001)
 if len(body)>3_000_000:raise ValueError("Oversized quote")
 return body

def run(output):
 now=datetime.now(timezone.utc)
 results=[]
 for symbol in TICKERS:
  record={"symbol":symbol,"status":"NOT_VERIFIED","record":None,"error":None,
          "source_url":BASE+TICKERS[symbol]+SUFFIX}
  try:
   record["record"]=parse(symbol,fetch(symbol),now)
   record["status"]=record["record"]["status"]
  except Exception as exc:
   record["error"]=type(exc).__name__+": "+str(exc)[:300]
  results.append(record)
 obj={"schema_version":"sgx-secondary-intraday-v114",
      "attempted_at_utc":now.isoformat(),
      "research_provider":"YAHOO_FINANCE_UNOFFICIAL",
      "retrieved_intraday_chart_count":sum(x["record"] is not None for x in results),
      "official_exchange_trade_data_count":0,
      "promoted_to_financial_feed":False,"ranking_eligible":False,"records":results}
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return obj

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();o=run(a.output)
 print("SGX secondary intraday research:",o["retrieved_intraday_chart_count"])
