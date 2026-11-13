"""v90: verify 3 consecutive UOB share buyback filings at original SGX URLs.

Dates 10, 11, 12 November 2026. Check issuer, SGX announcement reference,
Section D closing stock counts, and exact day-to-day change. This
cannot validate 13-Nov secondary claim or any November-14 market price.
"""
import argparse,hashlib,json
from pathlib import Path
from sgx_primary_buyback_v84 import parse,fetch

NOTICES=[
 ("2026-11-10","SG261110OTHRQ7Q7","https://links.sgx.com/1.0.0/corporate-announcements/Y0NT6GHJQAPLSMVQ/58e79d1d9d9600964459eebacee1ddcafc278a5ae3bfa3fac4da267e7247d75c",1646779591,14548000),
 ("2026-11-11","SG261111OTHRGYNT","https://links.sgx.com/1.0.0/corporate-announcements/OGJOD7K9GS51JRLV/cab40affb30af649a2f5a37c76072f84a0e1497d6fae97787c4c968bc7c120cc",1646745591,14548000),
 ("2026-11-12","SG261112OTHRSYPK","https://links.sgx.com/1.0.0/corporate-announcements/MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d",1646711591,14548000),
]

def verify(download=fetch):
 records=[]
 for day,ref,url,expected_net,expected_treasury in NOTICES:
  raw=download(url)
  r=parse("U11",url,raw,ref,day)
  if (r.get("issued_excluding_treasury")!=expected_net
      or r.get("treasury_shares")!=expected_treasury
      or r.get("issued_including_treasury_derived")!=expected_net+expected_treasury):
   raise ValueError("Official SGX UOB Section D count changed on "+day)
  records.append(r)
 for before,after in zip(records,records[1:]):
  if (before["issued_excluding_treasury"]-after["issued_excluding_treasury"]!=34000
      or before["treasury_shares"]!=after["treasury_shares"]
      or before["issued_including_treasury_derived"]-after["issued_including_treasury_derived"]!=34000):
   raise ValueError("Consecutive official UOB shares do not reconcile")
 return {"symbol":"U11",
   "status":"ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED",
   "issuer":"UNITED OVERSEAS BANK LIMITED",
   "records":records,
   "consecutive_day_net_decrease":34000,
   "treasury_constant":True,
   "latest_primary_in_chain":"2026-11-12",
   "later_2026_11_13_claim_verified":False,
   "not_proof_of_latest_as_of_today":True,
   "current_market_cap_eligible":False,
   "ranking_eligible":False}

def run(output,download=fetch):
 item={"symbol":"U11","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  proof=verify(download)
  item["status"]=proof["status"];item["record"]=proof
 except Exception as exc:
  item["error"]=f"{type(exc).__name__}: {str(exc)[:350]}"
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return item

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 proof=run(a.output)
 print(proof["status"],proof["error"])
 raise SystemExit(0 if proof["record"] is not None else 1)
