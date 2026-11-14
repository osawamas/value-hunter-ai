"""v161 date-coherent share and price evidence — explicit fail closed.

Do not let refresh-date or 180-day freshness mask a mismatch between
historical treasury-adjusted shares and Yahoo reference trade date.
This diagnostic NEVER changes finance feed, PER, PBR or ranking.
"""
import argparse,hashlib,json
from datetime import date,datetime,timezone
from pathlib import Path

def day(value):
 if not isinstance(value,str):raise ValueError("Date absent")
 try:return date.fromisoformat(value[:10])
 except ValueError:raise ValueError("Not ISO date")
def reconcile(feed,g13,s63):
 if feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_enabled") is not False or feed.get("ranking_eligible_count")!=0:
  raise ValueError("Ranking safety condition not present")
 if (g13.get("schema_version")!="sgx-g13-h1-direct-primary-share-confirmation-v127" or
     g13.get("published_june30_count_original_primary_supported") is not True or
     g13.get("shares_after_june30_unchanged_verified") is not False or
     g13.get("ranking_eligible") is not False):
  raise ValueError("G13 dated original not independently resolved")
 if (s63.get("schema_version")!="sgx-share-snapshot-difference-v110" or
     s63.get("published_reference_is_older") is not True or
     s63.get("current_shares_verified") is not False or
     s63.get("ranking_eligible") is not False):
  raise ValueError("S63 original snapshot status invalid")
 rows=[]
 for symbol in ("G13","S63"):
  records=[x for x in feed.get("records",[]) if x.get("symbol")==symbol]
  if len(records)!=1:raise ValueError("Registered issuer duplicate/absent")
  r=records[0]
  if (r.get("ranking_eligible") is not False or r.get("quote_source_type")!="YAHOO_FINANCE_UNOFFICIAL_CHART" or
      r.get("shares_count_basis")!="issued_excluding_treasury"):
   raise ValueError("Quote or shares source violates reference-only requirements")
  share_date=day(r.get("shares_as_of_date"));quote_date=day(r.get("quote_timestamp_utc"))
  if share_date!=date(2026,6,30) or quote_date!=date(2026,11,13):
   raise ValueError("Unexpected source-date basis or future upstream changes: revisit")
  days=(quote_date-share_date).days
  if days<=0:raise ValueError("Expected historical shares precede reference price")
  primary=g13 if symbol=="G13" else s63
  latest_date=day(primary["published_share_date"] if symbol=="G13" else primary["new_sgx_primary_snapshot_date"])
  latest_count=primary["issued_ex_treasury_at_june30"] if symbol=="G13" else primary["new_sgx_primary_issued_ex_treasury"]
  if symbol=="G13":
   if (r.get("shares_outstanding")!=latest_count or
       r.get("shares_pdf_sha256")!=primary["june30_primary_pdf_sha256"] or
       r.get("shares_source_url")!=primary["june30_halfyear_source_url"]):
    raise ValueError("G13 source binding or count mismatch")
  else:
   if (r.get("shares_outstanding")!=s63["published_financial_shares"] or
       r.get("shares_outstanding")==latest_count or
       r.get("shares_as_of_date")!=s63["published_financial_record_as_of_date"] or
       s63.get("new_minus_published_shares")!=latest_count-r["shares_outstanding"]):
    raise ValueError("S63 historical share discrepancy not consistent")
  rows.append({
   "symbol":symbol,
   "reference_share_snapshot_date":share_date.isoformat(),
   "reference_quote_trading_date":quote_date.isoformat(),
   "share_quote_reference_date_gap_days":days,
   "same_date_reconciled":False,
   "newest_observed_sgx_share_snapshot_date":latest_date.isoformat(),
   "newest_observed_sgx_shares_ex_treasury":latest_count,
   "reference_feed_shares_ex_treasury":r["shares_outstanding"],
   "newest_snapshot_is_currently_complete":False,
   "official_trade_tape_quote_confirmed":False,
   "reference_market_cap_per_pbr_temporally_verified":False,
   "ranking_eligible":False
  })
 return {"schema_version":"sgx-share-price-date-coherence-v161",
  "feed_updated_at_utc":feed["updated_at_utc"],
  "issuers_reviewed":len(rows),
  "mismatched_reference_date_count":len(rows),
  "official_trade_tape_verified_count":0,
  "ranking_eligible_count":0,
  "financial_feed_modified":False,
  "records":rows}

def main():
 p=argparse.ArgumentParser()
 for x in ("feed","g13","s63","output"):p.add_argument("--"+x,required=True)
 a=p.parse_args()
 feed_path=Path(a.feed);sha=hashlib.sha256(feed_path.read_bytes()).hexdigest()
 result=reconcile(*[json.loads(Path(x).read_text()) for x in (a.feed,a.g13,a.s63)])
 if hashlib.sha256(feed_path.read_bytes()).hexdigest()!=sha:raise ValueError("Finance feed changed")
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("v161: mismatches",result["mismatched_reference_date_count"])
if __name__=="__main__":main()
