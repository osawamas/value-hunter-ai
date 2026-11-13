"""v81: compare like-for-like 2026 vs 2025 bank issuer Q3 and 9M PDF rows.

Keep different duration metrics separate. Regression-check both present and
prior year columns. Values are parsed from the issuer PDF, not supplied by
a pricing feed. Not independently verified or an investable ranking signal.
"""
import argparse,hashlib,json,re
from pathlib import Path
from bank_q3_financials_v79 import SCHEMAS,SOURCES,amount
from official_http_v57 import get_pdf

COMPARISONS={
 "D05":{"profit_key":"net_profit","prior":{"Q3":{"total_income":5932,"net_profit":2954},
                                             "9M":{"total_income":17569,"net_profit":8675}}},
 "O39":{"profit_key":"group_net_profit","prior":{"Q3":{"total_income":3796,"group_net_profit":1978},
                                                   "9M":{"total_income":10998,"group_net_profit":5677}}},
 "U11":{"profit_key":"net_profit","prior":{"Q3":{"total_income":3398,"net_profit":443},
                                             "9M":{"total_income":10519,"net_profit":3271}}},
}
COLUMNS={"D05":{"Q3":(0,1),"9M":(5,6)},
         "O39":{"Q3":(0,1),"9M":(0,1)},
         "U11":{"Q3":(3,6),"9M":(0,1)}}

def read_pair(lines,label,symbol,period):
 matches=[i for i,line in enumerate(lines) if " ".join(line.lower().split())==label.lower()]
 if len(matches)!=1:raise ValueError("Ambiguous Q3 / nine-month issuer row: "+label)
 i=matches[0]
 tokens=[s.strip() for s in lines[i+1:] if s.strip()]
 current_index,prior_index=COLUMNS[symbol][period]
 if len(tokens)<=max(current_index,prior_index):
  raise ValueError("Issuer trading-update table shortened")
 return (amount(tokens[current_index]),amount(tokens[prior_index]))

def parse_pdf(symbol,raw):
 import fitz
 if symbol not in COMPARISONS:raise ValueError("Unexpected bank")
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
  raise ValueError("Official issuer PDF missing")
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)<max(SCHEMAS[symbol]["pages"].values()):raise ValueError("Missing issuer table page")
  first=" ".join(doc[i].get_text("text") for i in range(min(3,len(doc)))).lower()
  if SOURCES[symbol]["identity"][0].lower() not in first:
   raise ValueError("Bank identity absent")
  out={}
  for period in ("Q3","9M"):
   page=SCHEMAS[symbol]["pages"][period]
   lines=doc[page-1].get_text("text").splitlines()
   header=" ".join(lines[:85]).lower()
   if symbol=="D05":
    if not (re.search(r"3rd\s+qtr\s+2026",header) and re.search(r"9\s+mths\s+2026",header)
            and re.search(r"3rd\s+qtr\s+2025",header) and re.search(r"9\s+mths\s+2025",header)):
     raise ValueError("DBS comparable year column headers missing")
   elif symbol=="O39":
    required=("3q26","3q25") if period=="Q3" else ("9m26","9m25")
    if not all(x in header for x in required):raise ValueError("OCBC comparable period header absent")
   else:
    if not all(x in header for x in ("9m26","9m25","3q26","3q25")):
     raise ValueError("UOB comparable period header absent")
   current={}
   prior={}
   for metric in ("total_income",COMPARISONS[symbol]["profit_key"]):
    label=SCHEMAS[symbol]["rows"][metric][0]
    now,previous=read_pair(lines,label,symbol,period)
    expected=SCHEMAS[symbol]["rows"][metric][1 if period=="Q3" else 2]
    expected_prior=COMPARISONS[symbol]["prior"][period][metric]
    if (now,previous)!=(expected,expected_prior):
     raise ValueError(f"{symbol} {period} {metric} source/current/previous-year regression mismatch")
    if previous<=0 or now<0:raise ValueError("Year-over-year denominator invalid")
    current[metric]=now
    prior[metric]=previous
   growth={metric:round(100*(current[metric]/prior[metric]-1),2) for metric in current}
   out[period]={
    "period_end_2026":"2026-09-30",
    "period_end_2025":"2025-09-30",
    "period_start_2026":"2026-07-01" if period=="Q3" else "2026-01-01",
    "period_start_2025":"2025-07-01" if period=="Q3" else "2025-01-01",
    "duration":"THREE_MONTHS" if period=="Q3" else "NINE_MONTHS_YTD",
    "unit":"SGD_millions",
    "pdf_page_number":page,
    "current_year":current,"prior_year":prior,
    "growth_pct":growth,
   }
  return {"symbol":symbol,"status":"BANK_Q3_9M_YEAR_ON_YEAR_SAME_PERIOD_PDF_RECONCILED",
          "released_at_date":SOURCES[symbol]["released"],
          "q3":out["Q3"],"nine_months":out["9M"],
          "ranking_eligible":False,"independent_verification":False}
 finally:doc.close()

def run(symbol,output,raw=None):
 record={"symbol":symbol,"status":"NOT_VERIFIED",
         "source_url":SOURCES[symbol]["url"],"pdf_sha256":None,"record":None,"error":None}
 try:
  data=get_pdf(SOURCES[symbol]["url"],max_bytes=75_000_000,timeout=90) if raw is None else raw
  record["pdf_sha256"]=hashlib.sha256(data).hexdigest()
  record["record"]=parse_pdf(symbol,data)
  record["status"]="BANK_Q3_9M_YEAR_ON_YEAR_SAME_PERIOD_PDF_RECONCILED"
 except Exception as exc:
  record["error"]=f"{type(exc).__name__}: {str(exc)[:320]}"
 p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return record

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--symbol",choices=tuple(COMPARISONS),required=True)
 p.add_argument("--output",required=True);p.add_argument("--offline-pdf")
 a=p.parse_args()
 record=run(a.symbol,a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
 print(a.symbol,record["status"],record["error"])
 raise SystemExit(0 if record["status"]=="BANK_Q3_9M_YEAR_ON_YEAR_SAME_PERIOD_PDF_RECONCILED" else 1)
