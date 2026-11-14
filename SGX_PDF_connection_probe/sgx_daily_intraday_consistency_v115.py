"""v115: compare separately retrieved daily vs intraday Yahoo SGX bank chart bars.

Agreement is a provider-internal consistency check, NOT independent SGX proof.
"""
import argparse,json
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
BANKS=("D05","O39","U11")

def n(v):
 if type(v) not in (int,float) or not 0<v<10000:
  raise ValueError("Price value invalid")
 return Decimal(str(v)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)

def compare(daily,intraday):
 if (daily.get("schema_version")!="sgx-secondary-quote-probe-v112" or
     daily.get("source_kind")!="YAHOO_UNOFFICIAL_DAILY_CHART" or
     daily.get("promote_to_financial_feed") is not False or
     intraday.get("schema_version")!="sgx-secondary-intraday-v114" or
     intraday.get("research_provider")!="YAHOO_FINANCE_UNOFFICIAL" or
     intraday.get("promoted_to_financial_feed") is not False):
  raise ValueError("Untrusted input state")
 a=daily.get("records");b=intraday.get("records")
 if not isinstance(a,list) or not isinstance(b,list):
  raise ValueError("Record lists missing")
 if len(a)!=3 or len(b)!=3 or {x.get("symbol") for x in a}!=set(BANKS) or {x.get("symbol") for x in b}!=set(BANKS):
  raise ValueError("Required 3 unique bank symbols")
 aa={x["symbol"]:x for x in a};bb={x["symbol"]:x for x in b}
 records=[]
 for symbol in BANKS:
  x=aa[symbol].get("record");y=bb[symbol].get("record")
  if not isinstance(x,dict) or not isinstance(y,dict):
   raise ValueError("An actual observed chart was not retrieved")
  if (x.get("status")!="SECONDARY_YAHOO_DAILY_CHART_RESEARCH_ONLY" or
      y.get("status")!="YAHOO_SGX_INTRADAY_BAR_RESEARCH_ONLY" or
      x.get("symbol")!=symbol or y.get("symbol")!=symbol or
      x.get("provider_symbol")!=symbol+".SI" or y.get("provider_symbol")!=symbol+".SI" or
      x.get("actual_exchange_last_trade_timestamp_verified") is not False or
      y.get("bar_timestamp_is_verified_trade_time") is not False or
      y.get("price_independently_exchange_confirmed") is not False or
      x.get("ranking_eligible") is not False or y.get("ranking_eligible") is not False):
   raise ValueError("Quote verification or symbol claim invalid")
  if x.get("daily_bar_date_sgt")!=y.get("last_bar_date_sgt"):
   raise ValueError("Daily and intraday date mismatch")
  d=n(x["close_sgd_research"]);i=n(y["last_bar_price_sgd"])
  records.append({
   "symbol":symbol,"session_date_sgt":x["daily_bar_date_sgt"],
   "daily_close_sgd":str(d),"last_5m_bar_price_sgd":str(i),
   "rounded_price_matches":d==i,
   "provider_internal_only":True,
   "secondary_prices_independently_verified":False,
   "sgx_trade_execution_timestamp_verified":False,
   "valuation_eligible":False,"ranking_eligible":False
  })
 return {
  "schema_version":"sgx-yahoo-daily-intraday-consistency-v115",
  "date_and_symbol_matched_count":len(records),
  "matching_price_count":sum(x["rounded_price_matches"] for x in records),
  "same_provider_internal_consistency_only":True,
  "official_exchange_confirmed_quotes":0,
  "financial_feed_modified":False,"ranking_eligible":False,"records":records
 }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--daily",required=True);p.add_argument("--intraday",required=True)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 z=compare(json.loads(Path(a.daily).read_text()),json.loads(Path(a.intraday).read_text()))
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(z,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Matched daily vs 5m same provider",z["matching_price_count"])

if __name__=="__main__":main()
