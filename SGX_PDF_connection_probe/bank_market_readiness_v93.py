"""v93: bank-only market readiness and missing-primary-source diagnostics.

A dated 12-Nov SGX UOB repurchase confirmation, even with a consistent
13-Nov secondary copy, cannot be a current valuation share count.
Bank 2026 issuer income data is not a substitute for timestamped quotes.
"""
import argparse,json
from pathlib import Path

BANKS=("D05","O39","U11")
ISSUES={
 "D05":("UP_TO_DATE_ISSUED_EX_TREASURY_SHARES_NOT_VERIFIED",
        "TIME_STAMPED_SGX_SGD_SHARE_QUOTE_MISSING",
        "BANK_FINANCIALS_NO_INDEPENDENT_NUMERICAL_CROSSCHECK"),
 "O39":("OCBC_NOV12_TREASURY_TRANSFER_PRIMARY_PDF_NOT_VERIFIED",
        "UP_TO_DATE_ISSUED_EX_TREASURY_SHARES_NOT_VERIFIED",
        "TIME_STAMPED_SGX_SGD_SHARE_QUOTE_MISSING",
        "BANK_FINANCIALS_NO_INDEPENDENT_NUMERICAL_CROSSCHECK"),
 "U11":("UOB_NOV13_BUYBACK_PRIMARY_SGX_NOTICE_NOT_VERIFIED",
        "UP_TO_DATE_ISSUED_EX_TREASURY_SHARES_NOT_VERIFIED",
        "TIME_STAMPED_SGX_SGD_SHARE_QUOTE_MISSING",
        "BANK_FINANCIALS_NO_INDEPENDENT_NUMERICAL_CROSSCHECK"),
}

def annotate(feed):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Unexpected public feed")
 output=json.loads(json.dumps(feed))
 bank_rows=[r for r in output.get("records",[]) if r.get("symbol") in BANKS]
 if sorted(r.get("symbol") for r in bank_rows)!=sorted(BANKS):
  raise ValueError("Bank symbol coverage incomplete or ambiguous")
 for r in bank_rows:
  symbol=r["symbol"]
  if (r.get("bank_financial_state",{}).get("status")
      !="AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"):
   raise ValueError("Bank audited issuer Group statement status not checked")
  if (r.get("banking_interim_2026",{}).get("status")
      !="ISSUER_3Q_AND_NINE_MONTH_TRADING_UPDATE_REGRESSION_MATCHED"):
   raise ValueError("Bank 2026 financial interim source missing")
  if (r.get("ranking_eligible") is not False or
      any(r.get(k) is not None for k in ("price_sgd","shares_outstanding",
                 "market_cap_sgd","per_reference","pbr_reference_unverified","pbr_verified"))):
   raise ValueError("Bank valuation unexpectedly non-null")
  if symbol=="U11":
   chain=r.get("bank_primary_three_day_chain") or {}
   pending=r.get("bank_pending_buyback_consistency") or {}
   if (chain.get("status")!="ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED"
       or pending.get("status")!="SECONDARY_NOV13_ARITHMETICALLY_CONSISTENT_PRIMARY_NOT_VERIFIED"
       or pending.get("latest_current_shares_verified") is not False):
    raise ValueError("UOB recent official/secondary gap not independently recorded")
  if symbol=="O39":
   lead=r.get("bank_share_discovery") or {}
   if (lead.get("status")!="SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"
       or lead.get("sgx_announcement_reference")!="SG261112OTHRXH64"
       or lead.get("primary_sgx_announcement_url") is not None):
    raise ValueError("OCBC missing primary treasury-transfer proof")
  r["bank_market_readiness"]={
   "status":"NOT_READY_PRIMARY_SHARES_AND_TIMED_QUOTES_MISSING",
   "required_checks":list(ISSUES[symbol]),
   "2025_audited_issuer_group_available":True,
   "2026_q3_and_9m_issuer_financials_available":True,
   "2026_historical_share_records_not_current":True,
   "newest_discovered_event_primary_verified":False if symbol in ("U11","O39") else None,
   "official_current_share_count_verified":False,
   "current_quote_timestamp_verified":False,
   "sgd_quote_source_verified":False,
   "bank_valuation_eligible":False,
   "investment_ranking_eligible":False,
  }
 return output

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 result=annotate(json.loads(Path(a.input).read_text(encoding="utf-8")))
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("3 bank share/price readiness statuses remain not-eligible")
