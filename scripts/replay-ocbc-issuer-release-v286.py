#!/usr/bin/env python3
"""v286: cross-source issuer HOSTED OCBC FY2026 Q3 release (no market data).
This is second transport/publication by same issuer, not independent audit.
Compare rounded press-release SGD billions with existing SGX filing SGD millions.
"""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import re
import urllib.request
import urllib.error

ROOT=pathlib.Path(__file__).resolve().parent.parent
OFFICIAL_URL="https://www.ocbc.com/group/media/release/2026/ocbc-group-third-quarter-2026-results.page"
MAX_BYTES=1_500_000
class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def source_rows():
    data=json.loads((ROOT/"docs/data/sgx-big3-bank-research-v186.json").read_text())
    if(data["schema_version"]!="sgx-big3-normalized-bank-quarters-v186" or
       data["period_end"]!="2026-09-30" or data["unit"]!="SGD_millions" or
       data["ranking_eligible"] is not False):
        raise ValueError("SGX bank source changed")
    o=[x for x in data["entries"] if x["symbol"]=="O39"]
    if len(o)!=1 or o[0]["q3profit"]!=2042 or o[0]["nineprofit"]!=6237 or
       o[0]["q3nii"]!=2313 or o[0]["ninenii"]!=6798):
        raise ValueError("OCBC SGX source numbers changed")
    return o[0]
def rounded_matches(text,bank):
    norm=" ".join(text.replace("\u00a0"," ").split())
    keys={
     "period_3q":"third quarter",
     "period_9m":"first nine months",
     "issuer":"OCBC Group",
     "year":"2026",
     "q3":"2.04 billion",
     "nine":"6.24 billion",
     "q3_nii":"2.31 billion",
     "nine_nii":"6.80 billion"
    }
    lower=norm.lower()
    seen={k:v.lower() in lower for k,v in keys.items()}
    # Public press release values are rounded to S$0.01b; represent
    # intervals [round billion - 5m, +5m), never pretend exact 2042.
    precise={
       "q3profit":bank["q3profit"],"nineprofit":bank["nineprofit"],
       "q3nii":bank["q3nii"],"ninenii":bank["ninenii"]
    }
    rounded={
       "q3profit":2040,"nineprofit":6240,
       "q3nii":2310,"ninenii":6800
    }
    comparisons={k:abs(precise[k]-rounded[k])<=5 for k in precise}
    # 6.80 billion in the release may be presented as 6.80, 6.8, or 6,798
    # million; do not conflate missing words with confirmed source.
    valid=all(seen.values()) and all(comparisons.values()) and "6 november 2026" in lower
    return {"issuer_release_text_matched":valid,
      "press_release_phrase_checks":seen,
      "SGX_precision_within_rounded_release_bounds":comparisons,
      "reported_rounding_only_not_exact_reverification":True,
      "independent_financial_audit_complete":False,
      "market_price_rights_verified":False,"ranking_eligible":False}
def fetch():
    bank=source_rows()
    body=b"";error=None
    try:
        req=urllib.request.Request(OFFICIAL_URL,headers={
          "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
          "Accept":"text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req,timeout=25) as reply:
            if reply.geturl()!=OFFICIAL_URL:raise ValueError("Redirected source")
            if "html" not in reply.headers.get("Content-Type","").lower():raise ValueError("Non-HTML response")
            body=reply.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES:raise ValueError("Unexpected large release")
        parser=PlainHTML()
        parser.feed(body.decode("utf-8",errors="replace"))
        check=rounded_matches(" ".join(parser.parts),bank)
    except (OSError,urllib.error.URLError,ValueError,TimeoutError) as exc:
        error=type(exc).__name__
        check={"issuer_release_text_matched":False,
               "reported_rounding_only_not_exact_reverification":True,
               "independent_financial_audit_complete":False,
               "market_price_rights_verified":False,"ranking_eligible":False}
    artifact={
      "schema_version":"ocbc-2026-3q-issuer-website-cross-source-v286",
      "retrieved_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "issuer":"OCBC","symbol":"O39","period_end":"2026-09-30",
      "original_issuer_press_release_url":OFFICIAL_URL,
      "issuer_sgx_attachment_url":bank["source"],
      "issuer_sgx_attachment_sha256":bank["sha"],
      "issuer_website_html_sha256":hashlib.sha256(body).hexdigest() if body else None,
      "issuer_website_html_bytes":len(body),
      "fetch_error":error,
      "check":check,
      "source_reproducible_without_quote_redistribution":True,
      "ranking_eligible_count":0}
    out=ROOT/"build/research/ocbc-3q-website-cross-check-v286.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n")
    print("v286 "+("ISSUER_CROSS_SOURCE_ROUNDING_PASS" if check["issuer_release_text_matched"]
                      else "NOT_RECONCILED")+
          " original_html_bytes="+str(len(body))+" sha256="+str(artifact["issuer_website_html_sha256"]))
if __name__=="__main__":fetch()
