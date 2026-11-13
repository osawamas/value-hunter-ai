"""v88: original SGX UOB buyback 12-Nov-2026, source-bound historical snapshot.

The original SGX corporate announcement URL is verified independently
from the 13-Nov secondary lead. Do not assert 12-Nov is the latest/current
market-date share count. No price, market cap, PER/PBR or ranking promotion.
"""
import argparse,json
from pathlib import Path
from sgx_primary_buyback_v84 import parse,fetch

URL="https://links.sgx.com/1.0.0/corporate-announcements/MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d"
REF="SG261112OTHRSYPK"
DATE="2026-11-12"

def run(output,raw=None):
 item={"symbol":"U11","status":"NOT_VERIFIED","source_url":URL,"record":None,"error":None}
 try:
  page=fetch(URL) if raw is None else raw
  verified=parse("U11",URL,page,REF,DATE)
  if (verified["issued_excluding_treasury"]!=1646711591
      or verified["treasury_shares"]!=14548000
      or verified["issued_including_treasury_derived"]!=1661259591):
   raise ValueError("SGX 12-Nov-2026 official UOB Section D regression mismatch")
  item["status"]="SGX_ORIGINAL_U11_2026_11_12_BUYBACK_RECONCILED"
  item["record"]=verified
 except Exception as exc:
  item["error"]=f"{type(exc).__name__}: {str(exc)[:320]}"
 target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return item

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 result=run(a.output)
 print(result["status"],result["error"])
 raise SystemExit(0 if result["record"] is not None else 1)
