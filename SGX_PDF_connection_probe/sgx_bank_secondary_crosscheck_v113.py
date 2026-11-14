"""v113: crosscheck actual dated Yahoo chart observations against stored secondary research.

This is corroboration of research-only historical closes, NOT an exchange
trade record or official execution timestamp; valuations remain disallowed.
"""
import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BANKS=("D05","O39","U11")
SOURCE_STATUS="SECONDARY_YAHOO_DAILY_CHART_RESEARCH_ONLY"
RESEARCH_STATUS="DATED_2026_11_13_THIRD_PARTY_PRICE_RESEARCH_NOT_LIVE"

def cents(n):
    if type(n) not in (int,float) or not 0<n<10000:
        raise ValueError("Invalid numeric price")
    return Decimal(str(n)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)

def compare(feed,secondary):
    if (feed.get("schema_version")!="value_hunter_web_v29" or
        feed.get("ranking_eligible_count")!=0 or feed.get("ranking_enabled") is not False or
        secondary.get("schema_version")!="sgx-secondary-quote-probe-v112" or
        secondary.get("source_kind")!="YAHOO_UNOFFICIAL_DAILY_CHART" or
        secondary.get("promote_to_financial_feed") is not False):
        raise ValueError("Unexpected source guard state")
    records={x["symbol"]:x for x in feed["records"] if x.get("symbol") in BANKS}
    other={x["symbol"]:x for x in secondary["records"] if x.get("symbol") in BANKS}
    if set(records)!=set(BANKS) or set(other)!=set(BANKS) or len(other)!=len(BANKS):
        raise ValueError("Missing/duplicate bank records")
    output=[]
    for symbol in BANKS:
        f=records[symbol]; r=f.get("bank_dated_quote_research") or {}
        if (r.get("status")!=RESEARCH_STATUS or
            r.get("quotation_currency")!="SGD" or
            r.get("secondary_market_sources_only") is not True or
            r.get("exchange_official_trade_record_verified") is not False or
            r.get("current_price_usable_for_valuation") is not False):
            raise ValueError("Published historical research invalid")
        obs=other[symbol].get("record")
        if (other[symbol].get("status")!=SOURCE_STATUS or
            not isinstance(obs,dict) or obs.get("status")!=SOURCE_STATUS or
            obs.get("symbol")!=symbol or obs.get("provider_symbol")!=symbol+".SI" or
            obs.get("source_url")!=other[symbol].get("source_url") or
            obs.get("original_sgx_exchange_source_verified") is not False or
            obs.get("actual_exchange_last_trade_timestamp_verified") is not False or
            obs.get("usable_for_market_cap") is not False or
            obs.get("ranking_eligible") is not False):
            raise ValueError("Live Yahoo research missing/unsafe")
        if r["historical_trade_date"]!=obs["daily_bar_date_sgt"]:
            raise ValueError("Different trading dates cannot be crosschecked")
        reference=cents(r["reference_close_sgd"])
        observed=cents(obs["close_sgd_research"])
        output.append({
            "symbol":symbol,"trade_date_sgt":r["historical_trade_date"],
            "stored_third_party_close_sgd":str(reference),
            "live_yahoo_daily_chart_close_sgd":str(observed),
            "two_secondary_research_values_equal_to_cent":reference==observed,
            "yahoo_source_url":obs["source_url"],
            "yahoo_chart_raw_sha256":obs["response_sha256"],
            "chart_daily_bar_timestamp_not_last_trade_time":True,
            "exchange_execution_price_verified":False,
            "independent_exchange_confirmation":False,
            "eligible_for_market_cap_per_pbr":False,
            "ranking_eligible":False
        })
    return {
        "schema_version":"sgx-bank-secondary-crosscheck-v113",
        "source_kind":"MULTIPLE_SECONDARY_SOURCES_NO_PRIMARY_EXCHANGE_VALIDATION",
        "all_three_research_closes_match":all(x["two_secondary_research_values_equal_to_cent"] for x in output),
        "reference_close_count":len(output),
        "official_sgx_price_verified_count":0,
        "published_financial_feed_modified":False,
        "ranking_eligible":False,
        "records":output
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--feed",required=True)
    p.add_argument("--secondary",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=compare(json.loads(Path(a.feed).read_text()),
                   json.loads(Path(a.secondary).read_text()))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("v113 matched:",sum(x["two_secondary_research_values_equal_to_cent"] for x in result["records"]),"/3")

if __name__=="__main__":main()
