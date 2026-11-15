#!/usr/bin/env python3
"""v287 second issuer-hosted DBS 3Q26 profit check; no market data or audit claim."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import urllib.request
import urllib.error
import re

ROOT=pathlib.Path(__file__).resolve().parent.parent
URL="https://www.dbs.com/newsroom/DBS_third_quarter_net_profit_at_SGD_2_81_billion"
class Words(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("style","script","noscript"):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ("style","script","noscript") and self.skip:self.skip-=1
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def research():
 data=json.loads((ROOT/"docs/data/sgx-big3-bank-research-v186.json").read_text())
 if data["schema_version"]!="sgx-big3-normalized-bank-quarters-v186" or data["period_end"]!="2026-09-30" or data["ranking_eligible"] is not False:
  raise ValueError("SGX normalized bank source invalid")
 items=[v for v in data["entries"] if v["symbol"]=="D05"]
 if len(items)!=1 or (items[0]["q3profit"],items[0]["nineprofit"])!=(2813,8822):
  raise ValueError("DBS source precision drift")
 return items[0]
def verify(body,bank):
 parser=Words();parser.feed(body.decode("utf-8",errors="replace"))
 plain=" ".join(" ".join(parser.parts).split()).lower()
 clues={
  "dbs_name":"dbs" in plain,
  "third_quarter":"third-quarter" in plain or "third quarter" in plain,
  "net_profit":"net profit" in plain,
  "q3_2026":"third-quarter 2026" in plain or "third quarter 2026" in plain,
  "nov5":"05 nov 2026" in plain or "5 november 2026" in plain or "05 november 2026" in plain,
  "q3_profit_rounded":bool(re.search(r"(?:sgd|s\$)\s*2\.81\s*billion",plain)),
  "nine_profit_rounded":bool(re.search(r"(?:sgd|s\$)\s*8\.82\s*billion",plain))
 }
 rounded={"q3profit":2810,"nineprofit":8820}
 SGX_precision_matches={k:abs(bank[k]-v)<=5 for k,v in rounded.items()}
 return {"all_source_clues_verified":all(clues.values()) and all(SGX_precision_matches.values()),
  "source_text_clues":clues,"rounded_profit_crosschecks":SGX_precision_matches,
  "not_an_independent_financial_audit":True,
  "current_issued_share_count_verified":False,"licensed_current_market_quote":False,
  "ranking_eligible":False}
def main():
 bank=research();body=b"";problem=None;result={"all_source_clues_verified":False}
 try:
  with urllib.request.urlopen(urllib.request.Request(URL,headers={
    "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
    "Accept":"text/html,application/xhtml+xml"}),timeout=25) as reply:
   if reply.geturl()!=URL or "html" not in reply.headers.get("Content-Type","").lower():
    raise ValueError("Unexpected redirect or content type")
   body=reply.read(1500001)
   if len(body)>1500000:raise ValueError("Body too large")
  result=verify(body,bank)
 except (OSError,urllib.error.URLError,ValueError,TimeoutError) as exc:
  problem=type(exc).__name__
 artifact={
  "schema_version":"dbs-3q26-issuer-newsroom-proof-v287",
  "captured_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
  "issuer":"DBS","code":"D05","source_url":URL,
  "source_html_sha256":hashlib.sha256(body).hexdigest() if body else None,
  "source_html_bytes":len(body),"source_fetch_problem":problem,
  "sgx_issuer_source_url":bank["source"],"sgx_issuer_source_sha256":bank["sha"],
  "sgx_q3_profit_exact_millions":bank["q3profit"],
  "sgx_nine_profit_exact_millions":bank["nineprofit"],
  "checks":result,"independent_audit_completed":False,
  "market_licence_verified":False,"ranking_eligible_count":0}
 out=ROOT/"build/research/dbs-official-newsroom-3q-v287.json"
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n")
 print("v287 "+("ISSUER_HOSTED_PROFIT_ROUNDING_PASS" if result["all_source_clues_verified"] else "NOT_RECONCILED")+
       " bytes="+str(len(body))+" sha256="+str(artifact["source_html_sha256"]))
if __name__=="__main__":main()
