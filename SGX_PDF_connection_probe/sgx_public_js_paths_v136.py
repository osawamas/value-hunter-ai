"""v136: discover literal source path leads inside SGX's public JS bundles.

Read-only public asset inspection. No endpoint is executed, no private keys
captured, and no official full-master/quote verification claimed.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen

EXPECTED_ROOT="https://www.sgx.com/securities/"
KEYWORDS=("api.sgx.com","api2.sgx.com","marketdata","stockcode","securitytype",
          "securities","tradingcode","quote","equities","stocks")

def parse(js,source):
 if not isinstance(js,bytes) or not 50<len(js)<12_000_000:
  raise ValueError("Invalid public JS bundle")
 if not source.startswith(EXPECTED_ROOT) or not source.endswith(".chunk.js"):
  raise ValueError("Only known official script assets")
 text=js.decode("utf-8","replace")
 counts={k:len(re.findall(re.escape(k),text,re.I)) for k in KEYWORDS}
 # Only retain host/path names, never URL query values potentially containing keys.
 complete=set()
 for m in re.finditer(r"https?://[a-z0-9._-]+(?:/[a-zA-Z0-9/_\-.]{2,120})?",text,re.I):
  u=urlparse(m.group(0))
  if u.hostname and (u.hostname.endswith(".sgx.com") or u.hostname=="sgx.com"):
   complete.add(u.hostname+u.path[:120])
 partial=set()
 for m in re.finditer(r"/(?:api|market-data|marketdata|v1|stock|securities)/[A-Za-z0-9/_\-.]{4,110}",text,re.I):
  partial.add(m.group(0)[:120])
 return {
  "source_script_url":source,
  "public_js_sha256":hashlib.sha256(js).hexdigest(),
  "public_js_bytes":len(js),
  "keyword_occurrences":counts,
  "official_domain_literal_paths":sorted(complete)[:40],
  "potential_relative_data_paths":sorted(partial)[:40],
  "official_json_api_confirmed":False,
  "market_data_endpoint_called":False,
  "complete_security_master_retrieved":False,
  "quote_verified":False,
  "ranking_eligible":False
 }

def fetch(url):
 if not url.startswith(EXPECTED_ROOT) or not url.endswith(".chunk.js"):
  raise ValueError("Non-SGX JS URL")
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 read-only-assets",
                          "Accept":"application/javascript,text/javascript,*/*"})
 with urlopen(req,timeout=30) as r:
  if r.geturl()!=url:raise ValueError("Unexpected redirect")
  raw=r.read(12_000_001)
 if len(raw)>12_000_000:raise ValueError("JS bundle size too large")
 return raw

def run(input_file,output):
 data=json.loads(Path(input_file).read_text())
 if data.get("schema_version")!="sgx-official-asset-discovery-v135" or not data.get("record"):
  raise ValueError("v135 source links not verified")
 resources=data["record"]["resources"]
 urls=[x["url"] for x in resources if x.get("kind")=="script" and
       x.get("hostname")=="www.sgx.com" and
       x.get("url","").startswith(EXPECTED_ROOT) and x.get("url","").endswith(".chunk.js")]
 if len(urls)!=2:raise ValueError("Expected 2 official referenced JS chunks")
 results=[]
 for url in urls:
  item={"url":url,"status":"NOT_RETRIEVED","evidence":None,"error":None}
  try:
   item["evidence"]=parse(fetch(url),url)
   item["status"]="PUBLIC_SGX_JS_LITERAL_PATHS_EXTRACTED"
  except Exception as exc:item["error"]=type(exc).__name__+": "+str(exc)[:240]
  results.append(item)
 r={"schema_version":"sgx-official-js-discovery-v136",
    "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
    "public_sgx_js_assets_inspected":sum(x["evidence"] is not None for x in results),
    "official_quote_api_confirmed":False,
    "official_complete_master_confirmed":False,
    "ranking_eligible":False,"records":results}
 dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return r
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--assets",required=True);a.add_argument("--output",required=True)
 p=a.parse_args();r=run(p.assets,p.output)
 print("Inspected SGX public JS assets",r["public_sgx_js_assets_inspected"])
