"""v79: strictly period-scoped, issuer-PDF-extracted Q3 vs 9M 2026 bank results.

All amounts are SGD millions. Never mix standalone Q3, 9M cumulative,
balance-sheet point-in-time, or historical FY2025. The issuer PDF is the
source of every extracted number. EXPECTED provides fail-closed regression
checks, not substitute values. No PER/PBR or ranking promotion.
"""
import argparse,hashlib,json,re
from pathlib import Path
from bank_q3_2026_probe_v77 import SOURCES
from official_http_v57 import get_pdf

# (PDF page, row title, expected Q3-2026, 9M-2026)
SCHEMAS={
 "D05":{"pages":{"Q3":7,"9M":7},"rows":{
    "total_income":("Total income",5845,17886),
    "net_interest_income":("Of which: Net interest income",3711,10786),
    "operating_expenses":("Expenses",2373,7022),
    "profit_before_allowances":("Profit before allowances and amortisation",3472,10864),
    "net_profit":("Net profit",2813,8822),
  }},
 "O39":{"pages":{"Q3":2,"9M":4},"rows":{
    "net_interest_income":("Net interest income",2313,6798),
    "non_interest_income":("Non-interest income",1420,4933),
    "total_income":("Total income",3733,11731),
    "operating_expenses":("Operating expenses",-1522,-4602),
    "group_net_profit":("Group net profit",2042,6237),
  }},
 "U11":{"pages":{"Q3":3,"9M":3},"rows":{
    "net_interest_income":("Net interest income",2278,6900),
    "net_fee_income":("Net fee income",733,2035),
    "other_non_interest_income":("Other non-interest income",370,1464),
    "total_income":("Total income",3381,10398),
    "operating_expenses":("Less: Total expenses",1570,4722),
    "operating_profit":("Operating profit",1811,5676),
    "net_profit":("Net profit",1250,4165),
  }},
}
# PDF tables: DBS columns Q3, Q3-prev, pct, Q2, pct, 9M, 9M-prev, pct;
# OCBC Q3 table Q3, last-Q3, YoY, Q2, QoQ; 9M table 9M, 9M-prev, YoY;
# UOB columns 9M, previous 9M, YoY, Q3, Q2, QoQ, previous Q3, YoY.
VALUE=re.compile(r"^[-+]?[0-9][0-9,]*$|^\\([0-9][0-9,]*\\)$")
def amount(token):
 token=token.strip()
 if not VALUE.fullmatch(token):
  raise ValueError("Unexpected bank numeric column")
 if token.startswith("("):return -int(token[1:-1].replace(",",""))
 return int(token.replace(",",""))

def extract_row(lines,label,symbol,period):
 """One unique exact row and expected table header, then selected value."""
 positions=[i for i,line in enumerate(lines) if " ".join(line.lower().split())==label.lower()]
 if len(positions)!=1:
  raise ValueError(f"{symbol} {period} ambiguous row {label}: {len(positions)}")
 i=positions[0]
 tokens=[line.strip() for line in lines[i+1:] if line.strip()]
 if symbol=="D05":
  # The next numeric fields are adjacent and occupy fixed columns 0..7
  idx=0 if period=="Q3" else 5
 elif symbol=="U11":
  idx=3 if period=="Q3" else 0
 else:idx=0
 # Percent change is sometimes 'NM'/'-' and therefore not numeric.
 if len(tokens)<idx+1:raise ValueError("Table row truncated")
 # All required preceding group columns for UOB have numbers:
 # 9M, 9M prior, YoY, Q3, prior Q2 etc, but an NM% cell is possible.
 # Individual row check guards against drift.
 return amount(tokens[idx])

def parse_pdf(symbol,raw):
 import fitz
 if symbol not in SCHEMAS:raise ValueError("Unsupported 2026 bank")
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
  raise ValueError("Not issuer official PDF")
 cfg=SCHEMAS[symbol]
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)<max(cfg["pages"].values()):raise ValueError("Q3 issuer PDF page missing")
  beginning=" ".join(doc[i].get_text("text") for i in range(min(3,len(doc)))).lower()
  if SOURCES[symbol]["identity"][0].lower() not in beginning:
   raise ValueError("Bank issuer identity failed")
  result={}
  for period in ("Q3","9M"):
   page=cfg["pages"][period]
   lines=doc[page-1].get_text("text").splitlines()
   headings=" ".join(lines[:85]).lower()
   if symbol=="D05":
    if not ("3rd qtr" in headings and "9 mths" in headings and "2026" in headings):
     raise ValueError("DBS period headers not confirmed")
   elif symbol=="O39":
    if period=="Q3" and not ("third quarter 2026 performance" in headings and "3q26" in headings):
     raise ValueError("OCBC Q3 table header not found")
    if period=="9M" and not ("nine months 2026 performance" in headings and "9m26" in headings):
     raise ValueError("OCBC 9M table header not found")
   else:
    if not ("9m26" in headings and "3q26" in headings and "9m25" in headings):
     raise ValueError("UOB mixed 9M/Q3 header not found")
   values={}
   for key,(label,q3,months) in cfg["rows"].items():
    expected=q3 if period=="Q3" else months
    actual=extract_row(lines,label,symbol,period)
    if actual!=expected:
     raise ValueError(f"{symbol} {period} {key}: issuer PDF figure {actual} differs from regression check {expected}")
    values[key]=actual
   if symbol=="O39" and (values["net_interest_income"]+values["non_interest_income"]!=values["total_income"]):
    raise ValueError("OCBC Group subtotal not reconciled")
   if symbol=="D05" and values["total_income"]-values["operating_expenses"]!=values["profit_before_allowances"]:
    raise ValueError("DBS Group income less expenses mismatch")
   if symbol=="U11":
    if (values["net_interest_income"]+values["net_fee_income"]+values["other_non_interest_income"]!=values["total_income"]
        or values["total_income"]-values["operating_expenses"]!=values["operating_profit"]):
     raise ValueError("UOB Group total income/operating profit mismatch")
   result[period]={"period_start":"2026-07-01" if period=="Q3" else "2026-01-01",
                   "period_end":"2026-09-30","duration":"THREE_MONTHS" if period=="Q3" else "NINE_MONTHS_YTD",
                   "unit":"SGD_millions","reporting_scope":"GROUP_ISSUER_TRADING_UPDATE",
                   "source_pdf_page":page,"metrics":values}
  return {"symbol":symbol,"status":"ISSUER_Q3_9M_2026_PDF_REGRESSION_MATCHED",
          "published_at_date":SOURCES[symbol]["released"],
          "reporting_year":2026,"period_end":"2026-09-30",
          "Q3":result["Q3"],"9M":result["9M"],
          "independently_verified":False,"ranking_eligible":False,
          "not_audited_annual_statement":True}
 finally:doc.close()

def run(symbol,output,raw=None):
 rec={"symbol":symbol,"status":"NOT_VERIFIED","source_url":SOURCES[symbol]["url"],
      "pdf_sha256":None,"record":None,"error":None}
 try:
  data=get_pdf(SOURCES[symbol]["url"],max_bytes=75_000_000,timeout=90) if raw is None else raw
  rec["pdf_sha256"]=hashlib.sha256(data).hexdigest()
  rec["record"]=parse_pdf(symbol,data)
  rec["status"]="ISSUER_Q3_9M_2026_PDF_REGRESSION_MATCHED"
 except Exception as exc:
  rec["error"]=f"{type(exc).__name__}: {str(exc)[:350]}"
 target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return rec

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--symbol",choices=tuple(SCHEMAS),required=True)
 p.add_argument("--output",required=True);p.add_argument("--offline-pdf")
 a=p.parse_args()
 record=run(a.symbol,a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
 print(a.symbol,record["status"],record["error"])
 raise SystemExit(0 if record["status"]=="ISSUER_Q3_9M_2026_PDF_REGRESSION_MATCHED" else 1)
