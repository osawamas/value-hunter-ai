"""v129: match S63 Yahoo reference historical close and EODData capture.

Distinct websites are not guaranteed distinct upstream market providers.
The SGX buyback shares are a dated corporate action, not live valuation.
"""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP

def cents(v):
 if type(v) not in (float,int) or v<=0 or v>=10000:raise ValueError("Invalid price")
 return Decimal(str(v)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)

def compare(feed,eod,buyback):
 if (feed.get("schema_version")!="value_hunter_web_v29" or
     feed.get("ranking_eligible_count")!=0 or
     feed.get("ranking_enabled") is not False):
  raise ValueError("Financial feed untrusted")
 matches=[x for x in feed.get("records",[]) if x.get("symbol")=="S63"]
 if len(matches)!=1:raise ValueError("S63 not unique")
 f=matches[0]
 if (f.get("quote_source_type")!="YAHOO_FINANCE_UNOFFICIAL_CHART" or
     f.get("ranking_eligible") is not False or
     not str(f.get("quote_timestamp_utc","")).startswith("2026-11-13") or
     f.get("price_sgd") is None):
  raise ValueError("Published Yahoo reference quote not properly dated")
 if (eod.get("schema_version")!="sgx-s63-second-site-price-v128" or
     eod.get("status")!="SECONDARY_EODDATA_S63_HISTORICAL_CLOSE_MATCHED" or
     not isinstance(eod.get("record"),dict)):
  raise ValueError("EODData source not actually retrieved")
 e=eod["record"]
 if (e.get("status")!=eod["status"] or e.get("symbol")!="S63" or
     e.get("trade_date_sgt")!="2026-11-13" or e.get("currency")!="SGD" or
     e.get("source_url")!=eod.get("requested_url") or
     e.get("different_website_from_yahoo") is not True or
     e.get("upstream_market_data_independence_verified") is not False or
     e.get("original_sgx_exchange_trade_tape_verified") is not False or
     e.get("ranking_eligible") is not False):
  raise ValueError("Second website provenance fields unsafe")
 if (buyback.get("schema_version")!="sgx-s63-buyback-original-v109" or
     buyback.get("status")!="SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT"):
  raise ValueError("Buyback original unavailable")
 b=buyback.get("record")
 if (not isinstance(b,dict) or b.get("symbol")!="S63" or
     b.get("purchase_date")!="2026-11-13" or
     b.get("issued_excluding_treasury_after_purchase")!=3115847115 or
     b.get("dated_historical_snapshot_only") is not True or
     b.get("allow_market_cap_or_per_pbr") is not False):
  raise ValueError("Dated share snapshot incompatible")
 first=cents(f["price_sgd"]);second=cents(e["close_sgd_research"])
 return {
  "schema_version":"sgx-s63-historical-close-second-website-v129",
  "symbol":"S63","session_date_sgt":"2026-11-13",
  "yahoo_reference_close_sgd":str(first),
  "eoddata_close_sgd":str(second),
  "two_website_close_values_match":first==second,
  "upstream_market_data_provider_independence_verified":False,
  "primary_exchange_execution_quote_verified":False,
  "original_sgx_share_snapshot_on_same_date":True,
  "original_sgx_shares_ex_treasury":b["issued_excluding_treasury_after_purchase"],
  "s63_11_13_shares_still_current_verified":False,
  "corporate_action_date_does_not_certify_quote_time":True,
  "yahoo_reference_url":f.get("quote_url"),
  "eoddata_original_url":e["source_url"],
  "eoddata_source_sha256":e["source_html_sha256"],
  "sgx_share_source_url":b["source_url"],
  "source_notes":"Two separately hosted price displays; exchange trade tape and upstream independence not certified",
  "market_cap_per_pbr_promoted":False,
  "ranking_eligible":False,
  "financial_feed_modified":False
 }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True);p.add_argument("--eod",required=True)
 p.add_argument("--buyback",required=True);p.add_argument("--output",required=True)
 x=p.parse_args()
 original=Path(x.feed);before=hashlib.sha256(original.read_bytes()).hexdigest()
 out=compare(json.loads(original.read_text()),
  json.loads(Path(x.eod).read_text()),json.loads(Path(x.buyback).read_text()))
 if before!=hashlib.sha256(original.read_bytes()).hexdigest():
  raise ValueError("Market reference feed modified")
 dest=Path(x.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("S63 second website historical close match:",out["two_website_close_values_match"])
if __name__=="__main__":main()
