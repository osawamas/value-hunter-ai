"""v80: publish issuer 3Q26 Q3 and 9M bank data in separate nested fields.

Never use these trading-update figures to overwrite the audited FY2025 Group
statements or derive shares, PER, PBR, ROE, or ranking eligibility. Preserve
identity/provenance, Q3 vs 9M year-to-date semantics, and source timestamps.
"""
import argparse,json,re
from pathlib import Path
from bank_q3_financials_v79 import SCHEMAS,SOURCES

STATUS="ISSUER_Q3_9M_2026_PDF_REGRESSION_MATCHED"

def attach(feed,document):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Unrecognized SGX public feed")
 symbol=document.get("symbol")
 if symbol not in SCHEMAS or document.get("status")!=STATUS:
  raise ValueError("Bank 3Q26 PDF has not passed issuer regression")
 r=document.get("record") or {}
 rows=[x for x in feed.get("records",[]) if x.get("symbol")==symbol]
 if len(rows)!=1 or r.get("symbol")!=symbol or r.get("status")!=STATUS:
  raise ValueError("Bank identity missing/duplicated")
 row=rows[0]
 if (row.get("bank_financial_state",{}).get("status")!="AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"
     or row.get("ranking_eligible") is not False
     or r.get("published_at_date")!=SOURCES[symbol]["released"]
     or r.get("period_end")!="2026-09-30"
     or r.get("ranking_eligible") is not False
     or r.get("independently_verified") is not False
     or r.get("not_audited_annual_statement") is not True
     or document.get("source_url")!=SOURCES[symbol]["url"]
     or not re.fullmatch("[0-9a-f]{64}",document.get("pdf_sha256",""))):
  raise ValueError("Bank source/report/verification state inconsistent")
 if any(row.get(k) is not None for k in
        ("price_sgd","market_cap_sgd","per_reference",
         "pbr_reference_unverified","pbr_verified","shares_outstanding")):
  raise ValueError("3Q source cannot backfill current price/shares/valuation")
 expected=SCHEMAS[symbol]
 for period,start,duration in (("Q3","2026-07-01","THREE_MONTHS"),
                               ("9M","2026-01-01","NINE_MONTHS_YTD")):
  segment=r.get(period) or {}
  values=segment.get("metrics") or {}
  if (segment.get("period_start")!=start or segment.get("period_end")!="2026-09-30"
      or segment.get("duration")!=duration or segment.get("unit")!="SGD_millions"
      or segment.get("reporting_scope")!="GROUP_ISSUER_TRADING_UPDATE"
      or segment.get("source_pdf_page")!=expected["pages"][period]
      or set(values)!=set(expected["rows"])):
   raise ValueError("Bank quarter/cumulative unit, scope, or columns mismatched")
  for key,(_,q3,m9) in expected["rows"].items():
   val=values.get(key)
   if type(val) is not int or val!=(q3 if period=="Q3" else m9):
    raise ValueError("Issuer quarterly regression count changed: "+key)
  if symbol=="O39" and values["total_income"]!=values["net_interest_income"]+values["non_interest_income"]:
   raise ValueError("OCBC Group 3Q / 9M revenue arithmetic mismatch")
  if symbol=="D05" and values["total_income"]-values["operating_expenses"]!=values["profit_before_allowances"]:
   raise ValueError("DBS Group income arithmetic mismatch")
  if symbol=="U11" and (values["total_income"]-values["operating_expenses"]!=values["operating_profit"]
       or abs(values["total_income"]-values["net_interest_income"]
              -values["net_fee_income"]-values["other_non_interest_income"])>1):
   raise ValueError("UOB Bank 3Q revenue arithmetic mismatch")
 out=json.loads(json.dumps(feed))
 target=next(x for x in out["records"] if x["symbol"]==symbol)
 target["banking_interim_2026"]={
  "status":"ISSUER_3Q_AND_NINE_MONTH_TRADING_UPDATE_REGRESSION_MATCHED",
  "symbol":symbol,"period_end":"2026-09-30",
  "issuer_release_date":r["published_at_date"],
  "source_url":document["source_url"],"pdf_sha256":document["pdf_sha256"],
  "Q3":r["Q3"],"nine_months":r["9M"],
  "not_annual_2025":True,"not_independently_verified":True,
  "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True);p.add_argument("--issuer-result",required=True)
 p.add_argument("--output",required=True);a=p.parse_args()
 src=json.loads(Path(a.feed).read_text(encoding="utf-8"))
 doc=json.loads(Path(a.issuer_result).read_text(encoding="utf-8"))
 out=attach(src,doc)
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("Published period-aware issuer bank 2026 interim:",doc["symbol"])
