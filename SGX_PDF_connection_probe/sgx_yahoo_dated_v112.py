"""v112: live, dated Yahoo chart research probe for SGX bank counters.

Secondary/non-exchange data only. A chart daily bar timestamp is not
a verified last-trade execution time. Absolutely no promotion to latest.json.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCES = {"D05":"D05.SI", "O39":"O39.SI", "U11":"U11.SI"}
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
TAIL = "?interval=1d&range=5d"
SGT=ZoneInfo("Asia/Singapore")

def parse(symbol, raw, retrieved_at=None):
    if symbol not in SOURCES or not isinstance(raw,bytes) or not 50<len(raw)<=2_000_000:
        raise ValueError("Unknown ticker or malformed quote bytes")
    obj=json.loads(raw)
    chart=obj.get("chart") if isinstance(obj,dict) else None
    if not isinstance(chart,dict) or chart.get("error") is not None:
        raise ValueError("Yahoo chart unavailable")
    res=chart.get("result")
    if not isinstance(res,list) or len(res)!=1:
        raise ValueError("Ambiguous market chart")
    data=res[0]
    meta=data.get("meta",{})
    if (meta.get("symbol")!=SOURCES[symbol] or meta.get("currency")!="SGD" or
        meta.get("exchangeTimezoneName")!="Asia/Singapore"):
        raise ValueError("Ticker, SGD or Singapore exchange timezone mismatch")
    if meta.get("instrumentType") not in ("EQUITY",):
        raise ValueError("Not an equity chart")
    dates=data.get("timestamp")
    quotes=data.get("indicators",{}).get("quote")
    if (not isinstance(dates,list) or not 1<=len(dates)<=10 or
        not isinstance(quotes,list) or len(quotes)!=1 or not isinstance(quotes[0],dict)):
        raise ValueError("Invalid chart time series")
    closes=quotes[0].get("close")
    if not isinstance(closes,list) or len(closes)!=len(dates):
        raise ValueError("Close bars do not correspond to dates")
    if (any(type(t) is not int or t<=0 for t in dates) or
        dates!=sorted(set(dates))):
        raise ValueError("Invalid/duplicate/unordered bars")
    valid=[(t,c) for t,c in zip(dates,closes)
           if type(c) in (float,int) and math.isfinite(c) and 0<c<10000]
    if not valid:
        raise ValueError("No finite positive close")
    t,close=valid[-1]
    observed=datetime.fromtimestamp(t,timezone.utc)
    now=retrieved_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Timezone aware retrieval required")
    age=now-observed
    if not timedelta(0)<=age<=timedelta(days=10):
        raise ValueError("Outdated or future chart bar")
    if observed.astimezone(SGT).date()>now.astimezone(SGT).date():
        raise ValueError("Future Singapore date")
    return {
        "symbol":symbol,"provider_symbol":SOURCES[symbol],
        "status":"SECONDARY_YAHOO_DAILY_CHART_RESEARCH_ONLY",
        "source_url":BASE+SOURCES[symbol]+TAIL,
        "response_sha256":hashlib.sha256(raw).hexdigest(),
        "close_sgd_research":round(float(close),6),
        "daily_bar_timestamp_utc":observed.isoformat(),
        "daily_bar_date_sgt":observed.astimezone(SGT).date().isoformat(),
        "retrieved_at_utc":now.astimezone(timezone.utc).isoformat(),
        "exchange_timezone":"Asia/Singapore",
        "actual_exchange_last_trade_timestamp_verified":False,
        "original_sgx_exchange_source_verified":False,
        "independent_price_crosscheck_completed":False,
        "usable_for_market_cap":False,
        "usable_for_per_pbr":False,
        "ranking_eligible":False
    }

def fetch(symbol):
    url=BASE+SOURCES[symbol]+TAIL
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 research",
                            "Accept":"application/json"})
    with urlopen(req, timeout=25) as r:
        if r.geturl()!=url:raise ValueError("Unapproved quote redirect")
        if "json" not in r.headers.get("Content-Type","").lower():
            raise ValueError("Non JSON quote response")
        raw=r.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("Oversized quote response")
    return raw

def run(path):
    now=datetime.now(timezone.utc)
    rows=[]
    for symbol in SOURCES:
        result={"symbol":symbol,"status":"NOT_VERIFIED",
                "source_url":BASE+SOURCES[symbol]+TAIL,"record":None,"error":None}
        try:
            result["record"]=parse(symbol,fetch(symbol),now)
            result["status"]=result["record"]["status"]
        except Exception as exc:
            result["error"]=type(exc).__name__+": "+str(exc)[:240]
        rows.append(result)
    output={"schema_version":"sgx-secondary-quote-probe-v112",
            "attempted_at_utc":now.isoformat(),
            "source_kind":"YAHOO_UNOFFICIAL_DAILY_CHART",
            "verified_exchange_quotes":0,
            "secondary_dated_chart_count":sum(bool(r["record"]) for r in rows),
            "promote_to_financial_feed":False,
            "eligible_for_market_cap_per_pbr":False,
            "ranking_eligible":False,"records":rows}
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    x=p.parse_args();o=run(x.output)
    print("Secondary quotes:",o["secondary_dated_chart_count"],"of",len(SOURCES))
