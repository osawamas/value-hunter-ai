"""v101: bounded pagination capability diagnostic for keyless StocksSG directory.

Free tier published as 10 req/min: at most three calls per diagnostic run.
No candidate data goes to verified docs/data/latest.json. Inspect whether
page/limit parameters are honoured by comparing returned ticker fingerprints.
"""
import argparse,hashlib,json
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
from sgx_companies_api_v98 import URL,parse

QUERIES=(
 ("default",{}),
 ("page2",{"page":"2"}),
 ("larger_limit",{"limit":"200"}),
)
def fetch(params):
 url=URL+("?" + urlencode(params) if params else "")
 parts=urlsplit(url)
 if parts.scheme!="https" or parts.netloc!="stocks.com.sg" or parts.path!="/api/v1/companies":
  raise ValueError("Off-domain company listing request")
 req=Request(url,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only","Accept":"application/json"})
 with urlopen(req,timeout=25) as response:
  if response.geturl()!=url:raise ValueError("Third-party company API redirect")
  raw=response.read(8_000_001)
 if len(raw)>8_000_000:raise ValueError("Oversized candidate response")
 return raw

def diagnose(call=fetch):
 snapshots=[]
 for label,params in QUERIES:
  result={"label":label,"query":params,"status":"NOT_VERIFIED","error":None}
  try:
   raw=call(params)
   parsed=parse(raw)
   original=json.loads(raw.decode("utf-8"))
   tickers={x["symbol"] for x in parsed["companies"]}
   result.update({
    "status":"PARTIAL_ISSUER_DIRECTORY_RESPONSE",
    "count":len(tickers),
    "source_sha256":hashlib.sha256(raw).hexdigest(),
    "symbols":sorted(tickers),
    "meta":original.get("meta") if isinstance(original.get("meta"),dict) else None,
    "overlap_known_seven":len(set(("S68","G13","S20","S63","D05","O39","U11"))&tickers),
   })
  except Exception as exc:
   result["error"]=f"{type(exc).__name__}: {str(exc)[:240]}"
  snapshots.append(result)
 good=[x for x in snapshots if x["status"]=="PARTIAL_ISSUER_DIRECTORY_RESPONSE"]
 verified=[set(x["symbols"]) for x in good]
 union=set().union(*verified) if verified else set()
 baseline=set(snapshots[0].get("symbols",[]))
 return {
  "status":"DIRECTORY_PAGINATION_DIAGNOSTIC_ONLY",
  "source_url":URL,
  "snapshots":snapshots,
  "distinct_candidate_symbols_in_all_responses":len(union),
  "page2_delivers_new_symbols":bool(len(snapshots)>1 and set(snapshots[1].get("symbols",[]))-baseline),
  "larger_limit_delivers_new_symbols":bool(len(snapshots)>2 and set(snapshots[2].get("symbols",[]))-baseline),
  "request_count":3,
  "complete_sgx_universe_verified":False,
  "candidate_market_valuation_eligible":False,
 }

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 result=diagnose()
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for item in result["snapshots"]:
  print(item["label"],item["status"],item.get("count"),"meta=",item.get("meta"),"error=",item.get("error"))
 print("CANDIDATE_UNION",result["distinct_candidate_symbols_in_all_responses"],"NEW_PAGE",result["page2_delivers_new_symbols"],"NEW_LIMIT",result["larger_limit_delivers_new_symbols"])
