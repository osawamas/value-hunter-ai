"""v135: enumerate same-page public SGX HTML script and resource references.

For endpoint discovery only; no third-party stocks silently promoted.
No evaluation or execution of untrusted script content.
"""
import argparse,hashlib,json
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse
from pathlib import Path
from datetime import datetime,timezone
from sgx_securities_prices_probe_v134 import fetch,URL

class Assets(HTMLParser):
 def __init__(self):
  super().__init__();self.refs=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=="script" and d.get("src"):
   self.refs.append(("script",d["src"]))
  if tag=="link" and d.get("href") and any(x in (d.get("rel") or "").lower() for x in
                                             ("preload","modulepreload","stylesheet")):
   self.refs.append(("link",d["href"]))
  if tag=="a" and d.get("href") and any(x in d["href"].lower() for x in (".csv",".xlsx",".json")):
   self.refs.append(("download_candidate",d["href"]))

def analyze(raw):
 if not isinstance(raw,bytes) or not 50<len(raw)<8_000_000:
  raise ValueError("Invalid original SGX HTML")
 p=Assets();p.feed(raw.decode("utf-8","replace"))
 unique=set();assets=[]
 for kind,ref in p.refs:
  url=urljoin(URL,ref)
  parsed=urlparse(url)
  if parsed.scheme!="https" or len(url)>1000:continue
  if (kind,url) in unique:continue
  unique.add((kind,url))
  assets.append({"kind":kind,"url":url,"hostname":parsed.hostname})
  if len(assets)>120:raise ValueError("Too many HTML resources")
 return {
  "schema_version":"sgx-official-page-public-resources-v135",
  "source_url":URL,"source_html_sha256":hashlib.sha256(raw).hexdigest(),
  "referenced_resource_count":len(assets),
  "javascript_resource_count":sum(x["kind"]=="script" for x in assets),
  "potential_static_download_links":sum(x["kind"]=="download_candidate" for x in assets),
  "resources":assets,
  "official_quote_endpoint_confirmed":False,
  "downloadable_master_confirmed":False,
  "market_data_fetched":False,
  "ranking_eligible":False
 }

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 out={"schema_version":"sgx-official-asset-discovery-v135",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":"NOT_VERIFIED","record":None,"error":None}
 try:
  raw,typ=fetch()
  if "html" not in typ.lower():raise ValueError("Not SGX HTML")
  out["record"]=analyze(raw)
  out["status"]="SGX_PAGE_RESOURCE_REFERENCES_OBSERVED"
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:250]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"],out["record"] and out["record"]["javascript_resource_count"])
if __name__=="__main__":main()
