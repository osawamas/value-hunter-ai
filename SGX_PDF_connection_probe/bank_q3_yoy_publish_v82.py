"""v82: attach source-matched, like-period 2026 vs 2025 bank YoY ratios.

The existing issuer 3Q and 9M output must have been published first.
Q3 and 9M are NOT interchangeable. Annual 2025 Group data stays untouched.
"""
import argparse,json,re
from pathlib import Path
from bank_q3_yoy_v81 import COMPARISONS,SOURCES

STATUS="BANK_Q3_9M_YEAR_ON_YEAR_SAME_PERIOD_PDF_RECONCILED"

def attach(feed,proof):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Unexpected SGX public feed")
 symbol=proof.get("symbol")
 if symbol not in COMPARISONS or proof.get("status")!=STATUS:
  raise ValueError("Q3 year-over-year comparison not verified")
 doc=proof.get("record") or {}
 if (doc.get("symbol")!=symbol or doc.get("status")!=STATUS
     or doc.get("ranking_eligible") is not False
     or doc.get("independent_verification") is not False
     or doc.get("released_at_date")!=SOURCES[symbol]["released"]
     or proof.get("source_url")!=SOURCES[symbol]["url"]
     or not re.fullmatch(r"[0-9a-f]{64}",proof.get("pdf_sha256",""))):
  raise ValueError("Year-over-year issuer source identity invalid")
 matched=[r for r in feed.get("records",[]) if r.get("symbol")==symbol]
 if len(matched)!=1:raise ValueError("Missing/duplicated bank")
 row=matched[0]
 interim=row.get("banking_interim_2026") or {}
 if (interim.get("status")!="ISSUER_3Q_AND_NINE_MONTH_TRADING_UPDATE_REGRESSION_MATCHED"
     or interim.get("pdf_sha256")!=proof.get("pdf_sha256")
     or interim.get("source_url")!=proof.get("source_url")
     or interim.get("issuer_release_date")!=doc.get("released_at_date")
     or row.get("ranking_eligible") is not False):
  raise ValueError("Comparative and current year bank PDFs differ")
 if any(row.get(k) is not None for k in (
      "price_sgd","shares_outstanding","market_cap_sgd",
      "per_reference","pbr_reference_unverified","pbr_verified")):
  raise ValueError("Unexpected bank market-data promotion")
 result={}
 for period,name,duration,start,priorstart in (
   ("q3","Q3","THREE_MONTHS","2026-07-01","2025-07-01"),
   ("nine_months","nine_months","NINE_MONTHS_YTD","2026-01-01","2025-01-01")):
  segment=doc.get(period) or {}
  published=interim.get(name) or {}
  if (segment.get("period_end_2026")!="2026-09-30"
      or segment.get("period_end_2025")!="2025-09-30"
      or segment.get("period_start_2026")!=start
      or segment.get("period_start_2025")!=priorstart
      or segment.get("duration")!=duration
      or segment.get("unit")!="SGD_millions"
      or segment.get("pdf_page_number")!=published.get("source_pdf_page")
      or published.get("duration")!=duration
      or published.get("period_start")!=start
      or published.get("period_end")!="2026-09-30"):
   raise ValueError("Prior/current quarters not comparable")
  key_profit=COMPARISONS[symbol]["profit_key"]
  current=segment.get("current_year") or {}
  prior=segment.get("prior_year") or {}
  grow=segment.get("growth_pct") or {}
  if set(current)!={"total_income",key_profit} or set(prior)!=set(current) or set(grow)!=set(current):
   raise ValueError("Incomplete comparable bank row")
  for metric in current:
   now=current[metric];old=prior[metric]
   expected=COMPARISONS[symbol]["prior"]["Q3" if name=="Q3" else "9M"][metric]
   if (type(now) is not int or type(old) is not int
       or old<=0 or now<0 or old!=expected
       or published.get("metrics",{}).get(metric)!=now
       or type(grow[metric]) not in (float,int)
       or abs(grow[metric]-round(100*(now/old-1),2))>0.0001):
    raise ValueError("Prior-year value/duration or growth calculation wrong")
  result[name]={
    "period_start_2026":start,"period_start_2025":priorstart,
    "period_end_2026":"2026-09-30","period_end_2025":"2025-09-30",
    "duration":duration,"unit":"SGD_millions",
    "current_year":current,"prior_year":prior,"growth_pct":grow,
    "source_pdf_page":segment["pdf_page_number"],
  }
 out=json.loads(json.dumps(feed))
 dest=next(r for r in out["records"] if r.get("symbol")==symbol)
 dest["banking_yoy_2026"]={
    "status":"BANK_GROUP_LIKE_FOR_LIKE_Q3_AND_9M_PDF_VERIFIED",
    "source_url":proof["source_url"],"pdf_sha256":proof["pdf_sha256"],
    "issuer_release_date":doc["released_at_date"],
    "Q3":result["Q3"],"nine_months":result["nine_months"],
    "not_annual_or_investment_valuation":True,
    "third_party_independent_verification":False,
    "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--source",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 result=attach(json.loads(Path(a.feed).read_text(encoding="utf-8")),
               json.loads(Path(a.source).read_text(encoding="utf-8")))
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("Published same-duration bank year-on-year source evidence")
