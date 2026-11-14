"""v125: latest ST Engineering 9M26 SGX presentation evidence (research only).

Presentation contains revenue and contract/order book, but not an independently
verified current share count or a complete audited income statement.
"""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen

URL="https://links.sgx.com/FileOpen/ST%20Engineering%209M2026%20Market%20Update.ashx?App=Announcement&FileID=911321"
def parse(text,sha):
 if not isinstance(text,str) or not 200<len(text)<150000:
  raise ValueError("PDF text not present")
 compact=" ".join(text.split())
 if not re.search(r"9M2026\s+Market Update",compact,re.I) or not re.search(r"13 November 2026",compact,re.I):
  raise ValueError("Wrong source or presentation date")
 if not re.search(r"Strong\s+9M\s+Revenue\s+Growth\s+of\s+10%\s+y-o-y",compact,re.I):
  raise ValueError("Original 9M reported growth not found")
 if not re.search(r"3Q2026",compact,re.I) or not re.search(r"9M2026",compact,re.I):
  raise ValueError("Financial period missing")
 if not all(v in compact for v in ("13.2b","37.7b","10.0b")):
  raise ValueError("Revenue, order book, contract wins not extracted")
 return {
  "status":"SGX_S63_OFFICIAL_NINE_MONTH_2026_PRESENTATION",
  "source_url":URL,"source_pdf_sha256":sha,
  "issuer":"Singapore Technologies Engineering Ltd","symbol":"S63",
  "report_date":"2026-11-13","period_end_date":"2026-09-30",
  "nine_month_revenue_sgd_billion_rounded":10.0,
  "nine_month_reported_revenue_yoy_pct":10,
  "nine_month_rebased_revenue_yoy_pct":13,
  "nine_month_contract_wins_sgd_billion_rounded":13.2,
  "order_book_2026_09_sgd_billion_rounded":37.7,
  "all_figures_rounding_disclosed":True,
  "audited_income_and_profit_for_new_per_verified":False,
  "current_price_or_shares_verified":False,
  "ranking_eligible":False,
  "valuation_recomputed":False
 }
def run(output):
 result={"schema_version":"sgx-s63-9m2026-update-v125",
    "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
    "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0",
                            "Accept":"application/pdf"})
  with urlopen(req,timeout=30) as r:
   if r.geturl()!=URL or "pdf" not in r.headers.get("Content-Type","").lower():
    raise ValueError("Not an original SGX-hosted PDF")
   raw=r.read(8_000_001)
  if not raw.startswith(b"%PDF") or len(raw)>8_000_000:
   raise ValueError("Invalid/oversized SGX PDF")
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"update.pdf";path.write_bytes(raw)
   text=subprocess.run(["pdftotext","-layout",str(path),"-"],
       capture_output=True,check=True,timeout=30,text=True).stdout
  result["record"]=parse(text,hashlib.sha256(raw).hexdigest())
  result["status"]=result["record"]["status"]
 except Exception as exc:
  result["error"]=type(exc).__name__+": "+str(exc)[:260]
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();o=run(a.output);print(o["status"],o["error"])
