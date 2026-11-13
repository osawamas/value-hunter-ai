"""v95: dated research-only SGX bank quote observations, never a live quote.

Static 2026-11-13 evidence from third-party market history pages:
SGinvestors and a separate historical quote site each agree on close.
Not fetched and independently crosschecked by this application at runtime.
Never populate price_sgd, shares_outstanding, market cap, PER/PBR or ranking.
"""
import argparse,json
from pathlib import Path

EVIDENCE={
 "D05":{
  "price":"69.900",
  "observations":[
   {"source":"SGinvestors SGX D05 share price history",
    "url":"https://sginvestors.io/sgx/stock/d05-dbs/share-price-history",
    "observed":"69.900"},
   {"source":"StockAnalysis SGX D05 history",
    "url":"https://stockanalysis.com/quote/sgx/D05/history/",
    "observed":"69.90"},
  ],
  "conflicting_source":{
    "source":"Investing.com DBS historical",
    "url":"https://www.investing.com/equities/dbs-group-holdings-historical-data",
    "displayed":"70.14",
    "reason":"CONFLICTS_WITH_TWO_CONCORDANT_HISTORY_SOURCES; NOT_ADOPTED",
  },
 },
 "O39":{
  "price":"28.530",
  "observations":[
   {"source":"SGinvestors SGX O39 share price history",
    "url":"https://sginvestors.io/sgx/stock/o39-ocbc-bank/share-price-history",
    "observed":"28.530"},
   {"source":"StockAnalysis SGX O39 history",
    "url":"https://stockanalysis.com/quote/sgx/O39/history/",
    "observed":"28.53"},
  ],
 },
 "U11":{
  "price":"37.750",
  "observations":[
   {"source":"SGinvestors SGX U11 stock-info",
    "url":"https://sginvestors.io/sgx/stock/u11-uob/stock-info",
    "observed":"37.750"},
   {"source":"EODData SGX U11 history",
    "url":"https://www.eoddata.com/stockquote/SGX/U11.htm",
    "observed":"37.75"},
  ],
 }
}
STATUS="DATED_2026_11_13_THIRD_PARTY_PRICE_RESEARCH_NOT_LIVE"

def attach(feed):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Wrong SGX feed schema")
 banks=[r for r in feed.get("records",[]) if r.get("symbol") in EVIDENCE]
 if len(banks)!=3 or set(r["symbol"] for r in banks)!=set(EVIDENCE):
  raise ValueError("Missing/duplicate listed bank")
 out=json.loads(json.dumps(feed))
 for row in out["records"]:
  symbol=row.get("symbol")
  if symbol not in EVIDENCE:continue
  if (row.get("ranking_eligible") is not False
      or row.get("bank_market_readiness",{}).get("status")
         !="NOT_READY_PRIMARY_SHARES_AND_TIMED_QUOTES_MISSING"
      or any(row.get(k) is not None for k in (
         "shares_outstanding","price_sgd","market_cap_sgd",
         "per_reference","pbr_reference_unverified","pbr_verified"))):
   raise ValueError("Research quote cannot overwrite investable market fields")
  evidence=EVIDENCE[symbol]
  val=float(evidence["price"])
  if val<=0 or len(evidence["observations"])!=2:
   raise ValueError("Invalid static quote research record")
  sources=set()
  for observation in evidence["observations"]:
   if (float(observation["observed"])!=val
       or not observation["url"].startswith("https://")
       or observation["url"] in sources):
    raise ValueError("Conflicting dated bank quote sources")
   sources.add(observation["url"])
  item={
   "status":STATUS,
   "historical_trade_date":"2026-11-13",
   "quotation_currency":"SGD",
   "price_type":"RESEARCH_COMPARABLE_DAILY_CLOSE",
   "reference_close_sgd":val,
   "sources":evidence["observations"],
   "secondary_market_sources_only":True,
   "static_observation_not_automated_live_fetch":True,
   "live_price_timestamp_verified":False,
   "exchange_official_trade_record_verified":False,
   "source_quote_delay_or_realtime_not_certified":True,
   "current_price_usable_for_valuation":False,
   "shares_count_verified_same_date":False,
   "ranking_eligible":False
  }
  if "conflicting_source" in evidence:
   item["price_source_disagreement"]=evidence["conflicting_source"]
  row["bank_dated_quote_research"]=item
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 output=attach(json.loads(Path(a.input).read_text(encoding="utf-8")))
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Three historical bank prices researched only; current quote fields untouched")
