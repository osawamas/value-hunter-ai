"""v134: SGX securities-prices page direct HTML disclosure probe.

This is NOT a downloaded official master or verified price feed.
It records page structure, source hash and whether any issuer rows are actually
present in server-side visible HTML (JavaScript may load data separately).
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://www.sgx.com/securities/securities-prices?code=stocks"
MARKERS=("Trading Name","Trading Code","ST Engineering","Genting Sing","G13","S63",
         "DBS","OCBC Bank","Download","As at")

class Visible(HTMLParser):
 def __init__(self):
  super().__init__();self.parts=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hidden+=1
  if tag in ("h1","h2","div","tr","td","th","span","p","li","br"):self.parts.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hidden:self.hidden-=1
  if tag in ("h1","h2","div","tr","td","th","span","p","li"):self.parts.append(" ")
 def handle_data(self,data):
  if not self.hidden:self.parts.append(data)

def inspect(raw,content_type="text/html"):
 if not isinstance(raw,bytes) or not 50<len(raw)<8_000_000:
  raise ValueError("SGX HTML response invalid")
 if "html" not in content_type.lower():
  raise ValueError("Not an HTML response")
 html=raw.decode("utf-8","replace")
 p=Visible();p.feed(html)
 visible=" ".join(" ".join(p.parts).split())
 markers={m:bool(re.search(re.escape(m),visible,re.I)) for m in MARKERS}
 ticker_presence={s:bool(re.search(r"\b"+s+r"\b",visible,re.I)) for s in
                  ("S63","G13","D05","O39","U11","S68","S20")}
 rendered_table=all(markers.get(m,False) for m in ("Trading Name","Trading Code")) and \
                sum(ticker_presence.values())>=3
 return {
  "schema_version":"sgx-official-page-html-probe-v134",
  "requested_url":URL,
  "html_response_sha256":hashlib.sha256(raw).hexdigest(),
  "response_bytes":len(raw),
  "visible_text_length":len(visible),
  "visible_markers":markers,
  "visible_expected_ticker_presence":ticker_presence,
  "page_contains_multi_ticker_visible_table_evidence":rendered_table,
  "js_rendering_or_access_failure_possible":not rendered_table,
  "complete_official_sgx_security_master_retrieved":False,
  "official_master_row_count_verified":None,
  "official_trade_time_quote_parsed":False,
  "eligible_for_ranking":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI official-reference-probe)",
                          "Accept":"text/html"})
 with urlopen(req,timeout=25) as r:
  if r.geturl()!=URL:raise ValueError("Unexpected exchange redirect")
  typ=r.headers.get("Content-Type","")
  raw=r.read(8_000_001)
 if len(raw)>8_000_000:raise ValueError("Oversized response")
 return raw,typ

def run(path):
 out={"schema_version":"sgx-securities-price-html-research-v134",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":"NOT_RETRIEVED","result":None,"error":None}
 try:
  raw,typ=fetch()
  out["result"]=inspect(raw,typ)
  out["status"]="SGX_OFFICIAL_HTML_RETRIEVED_STRUCTURE_ONLY"
 except Exception as e:
  out["error"]=type(e).__name__+": "+str(e)[:250]
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();r=run(a.output)
 print(r["status"],r["error"],r["result"] and r["result"]["page_contains_multi_ticker_visible_table_evidence"])
