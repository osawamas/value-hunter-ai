"""v98: test documented keyless StocksSG SGX company JSON directory API.

StocksSG describes /api/v1/companies and keyless 10 req/min free tier.
Source is THIRD-PARTY, not official SGX company register. Download only
a candidate issuer index, never a live quote or investment ranking input.
"""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://stocks.com.sg/api/v1/companies"
KNOWN=("S68","G13","S20","S63","D05","O39","U11")
SYMBOL=re.compile(r"^[A-Z0-9]{1,6}$")

def parse(raw):
 if not isinstance(raw,bytes) or not 2<=len(raw)<=8_000_000:
  raise ValueError("Company API body invalid")
 data=json.loads(raw.decode("utf-8"))
 if not isinstance(data,dict) or not isinstance(data.get("data"),list):
  raise ValueError("StocksSG API has unexpected data envelope")
 rows=data["data"]
 if len(rows)<20 or len(rows)>1200:
  raise ValueError("Third-party company directory too sparse or excessive")
 found={}
 rejected=0
 observed_keys=set()
 for item in rows:
  if not isinstance(item,dict):
   raise ValueError("Company JSON row not an object")
  observed_keys.update(item.keys())
  code=item.get("ticker") or item.get("symbol") or item.get("stock_code")
  company=item.get("company_name") or item.get("name")
  if (not isinstance(code,str) or not SYMBOL.fullmatch(code.strip().upper())
      or not isinstance(company,str) or len(company.strip())<3):
   rejected+=1;continue
  code=code.strip().upper()
  if code in found:
   raise ValueError("Duplicate candidate SGX company ticker "+code)
  found[code]=company.strip()
 if not found:
  raise ValueError("No issuer ticker/name fields in companies API")
 known=sorted(set(KNOWN)&set(found))
 return {
  "status":"THIRD_PARTY_COMPANY_JSON_CANDIDATES_DIAGNOSTIC_ONLY",
  "source_url":URL,"source_response_sha256":hashlib.sha256(raw).hexdigest(),
  "provider":"StocksSG",
  "raw_rows_count":len(rows),
  "accepted_candidates":len(found),"rejected_rows_count":rejected,
  "all_7_known_present":len(known)==7,
  "known_symbols_present":known,
  "known_symbols_missing":sorted(set(KNOWN)-set(known)),
  "observed_object_keys":sorted(observed_keys),
  "companies":[{"symbol":code,"display_name":name} for code,name in sorted(found.items())],
  "scope":"PARTIAL_THIRD_PARTY_DIRECTORY_NOT_OFFICIAL_SGX_REGISTRY",
  "all_sgx_listings_verified":False,
  "finance_independently_verified":False,
  "share_counts_independently_verified":False,
  "current_market_price_verified":False,
  "ranking_eligible":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only",
                          "Accept":"application/json"})
 with urlopen(req,timeout=25) as resp:
  if resp.geturl()!=URL:raise ValueError("Companies API redirect not approved")
  raw=resp.read(8_000_001)
  ctype=resp.headers.get("Content-Type","")
  if "json" not in ctype.lower():raise ValueError("Provider did not respond with JSON")
 if len(raw)>8_000_000:raise ValueError("Companies API oversized")
 return raw

def run(output,raw=None):
 record={"status":"NOT_VERIFIED","source_url":URL,"record":None,"error":None}
 try:
  body=fetch() if raw is None else raw
  record["record"]=parse(body)
  record["status"]=record["record"]["status"]
 except Exception as exc:
  record["error"]=f"{type(exc).__name__}: {str(exc)[:320]}"
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return record

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 result=run(a.output)
 print("Company API",result["status"],(result["record"] or {}).get("accepted_candidates",result["error"]))
 if result["record"]:print("Observed fields",result["record"]["observed_object_keys"][:35])
 raise SystemExit(0 if result["record"] else 1)
