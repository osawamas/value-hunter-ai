"""v86: publish direct SGX UOB 7-Sep shareholding as dated issuer evidence.

A confirmed primary filing on 7-Sep-2026 cannot be treated as the
current share count. The 30-Sep and Nov events are separately unresolved.
Never overwrite market quote, PER, PBR or ranking.
"""
import argparse,json,re
from pathlib import Path
from u11_primary_snapshot_v85 import URL,REF,DATE

STATUS="OFFICIAL_SGX_U11_2026_09_07_SECTION_D_VERIFIED_DIAGNOSTIC"

def attach(feed,proof):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("SGX public feed schema wrong")
 rows=[x for x in feed.get("records",[]) if x.get("symbol")=="U11"]
 if len(rows)!=1:
  raise ValueError("UOB record missing or duplicated")
 row=rows[0]
 report=proof.get("record") or {}
 if (proof.get("symbol")!="U11" or proof.get("status")!=STATUS
     or proof.get("source_url")!=URL
     or report.get("symbol")!="U11"
     or report.get("status")!="DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY"
     or report.get("reference")!=REF
     or report.get("as_of_date")!=DATE
     or report.get("source_url")!=URL
     or report.get("not_proof_of_latest") is not True
     or report.get("requires_additional_events_and_crosscheck") is not True
     or report.get("valuation_eligible") is not False
     or report.get("ranking_eligible") is not False
     or not re.fullmatch(r"[0-9a-f]{64}",report.get("primary_sgx_page_sha256",""))):
  raise ValueError("Direct SGX UOB provenance/date/issuer invalid")
 net=report.get("issued_excluding_treasury")
 treasury=report.get("treasury_shares")
 gross=report.get("issued_including_treasury_derived")
 if (type(net) is not int or type(treasury) is not int or type(gross) is not int
     or net!=1648956591 or treasury!=14160900
     or gross!=net+treasury):
  raise ValueError("Primary SGX UOB September Section D numbers invalid")
 if (row.get("ranking_eligible") is not False
     or any(row.get(key) is not None for key in
            ("price_sgd","shares_outstanding","market_cap_sgd",
             "per_reference","pbr_reference_unverified","pbr_verified"))):
  raise ValueError("UOB market or current share state not expected")
 other=row.get("bank_share_discovery") or {}
 if other and other.get("event_date","")<=DATE:
  raise ValueError("Later unverified UOB share event must remain distinct")
 out=json.loads(json.dumps(feed))
 target=next(x for x in out["records"] if x["symbol"]=="U11")
 target["bank_primary_share_history"]={
  "status":"ORIGINAL_SGX_DAILY_BUYBACK_2026_09_07_RECONCILED",
  "as_of_date":DATE,"sgxnet_reference":REF,
  "issued_excluding_treasury":net,
  "treasury_shares":treasury,
  "gross_issued_derived":gross,
  "primary_source_url":URL,
  "primary_html_sha256":report["primary_sgx_page_sha256"],
  "historical_only":True,
  "current_shares_not_verified":True,
  "subsequent_corporate_actions_not_reconciled":True,
  "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--source",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 result=attach(json.loads(Path(a.feed).read_text(encoding="utf-8")),
               json.loads(Path(a.source).read_text(encoding="utf-8")))
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Original SGX UOB 2026-09-07 historical notice published without live shares")
