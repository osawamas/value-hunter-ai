"""v108: two exact SGX official issuer-counter-ISIN links, strict primary HTML proof."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = {
    "U11": {
        "url": "https://links.sgx.com/1.0.0/corporate-announcements/EVZ7PV6QP0P5BMW5/e2580790f6fa4d225394e792ccd026674a9ed767eddb6a18355f1d4b3dadeb22",
        "issuer": "UNITED OVERSEAS BANK LIMITED",
        "security_name": "UNITED OVERSEAS BANK LIMITED",
        "isin": "SG1M31001969",
        "reference": "SG261015OTHR6VTS",
        "broadcast": "15-Oct-2026 17:24:00",
    },
    "O39": {
        "url": "https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/50dad2d3f2e1374d94921a9cad3497846885577d0c43cf2e1fe14c8c7f4764a6",
        "issuer": "OVERSEA-CHINESE BANKING CORPORATION LIMITED",
        "security_name": "OVERSEA-CHINESE BANKING CORP",
        "isin": "SG1S04926220",
        "reference": "SG261106OTHRI4L9",
        "broadcast": "06-Nov-2026 06:59:27",
    },
}
class Visible(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.hidden+=1
        if tag in ("p","div","span","li","h1","h2","h3","tr","td","br"):self.parts.append(" ")
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
        if tag in ("p","div","span","li","h1","h2","h3","tr","td"):self.parts.append(" ")
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def parse(symbol,raw):
    if symbol not in SOURCES or not isinstance(raw,bytes) or not 200<=len(raw)<=3_000_000:
        raise ValueError("Unknown security or invalid SGX page")
    expected=SOURCES[symbol]
    parsed=Visible();parsed.feed(raw.decode("utf-8","replace"))
    plain=" ".join(" ".join(parsed.parts).split())
    binding=(r"Issuer\s*/\s*Manager\s+"+re.escape(expected["issuer"])+
             r"\s+Securit(?:y|ies)\s+"+re.escape(expected["security_name"])+
             r"\s*-\s*"+expected["isin"]+r"\s*-\s*"+symbol+r"\b")
    if len(re.findall(binding,plain,re.I))!=1:
        raise ValueError("Issuer/security/ISIN/ticker relationship absent or ambiguous")
    independent_pair=(re.escape(expected["security_name"])+r"\s*-\s*"+
                      expected["isin"]+r"\s*-\s*"+symbol+r"\b")
    if len(re.findall(independent_pair,plain,re.I))!=1:
        raise ValueError("Security identity repeated or missing")
    if len(re.findall(r"Announcement Reference\s+"+expected["reference"]+r"\b",plain,re.I))!=1:
        raise ValueError("Announcement reference mismatch")
    if len(re.findall(r"Date\s*&\s*Time of Broadcast\s+"+
                      re.escape(expected["broadcast"])+r"\b",plain,re.I))!=1:
        raise ValueError("Broadcast timestamp mismatch")
    return {
        "status":"SGX_PRIMARY_HISTORICAL_COUNTER_ISIN_LINK_VERIFIED",
        "symbol":symbol,"issuer":expected["issuer"],"isin":expected["isin"],
        "source_url":expected["url"],"source_html_sha256":hashlib.sha256(raw).hexdigest(),
        "announcement_reference":expected["reference"],"broadcast_sgt_text":expected["broadcast"],
        "historical_identity_link_only":True,
        "today_listing_status_verified":False,
        "official_complete_master_verified":False,
        "quote_or_current_shares_verified":False,
        "eligible_for_market_cap_per_pbr":False,
        "eligible_for_ranking":False,
    }

def fetch(symbol):
    url=SOURCES[symbol]["url"]
    request=Request(url,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 primary-identity-research",
                                 "Accept":"text/html"})
    with urlopen(request,timeout=25) as resp:
        if resp.geturl()!=url:
            raise ValueError("Redirect from original SGX URL")
        if "html" not in resp.headers.get("Content-Type","").lower():
            raise ValueError("Official source not HTML")
        raw=resp.read(3_000_001)
    if len(raw)>3_000_000:raise ValueError("Official source oversized")
    return raw

def run(output):
    records=[]
    for symbol,setting in SOURCES.items():
        entry={"symbol":symbol,"requested_url":setting["url"],
               "status":"NOT_VERIFIED","record":None,"error":None}
        try:
            entry["record"]=parse(symbol,fetch(symbol))
            entry["status"]=entry["record"]["status"]
        except Exception as exc:
            entry["error"]=type(exc).__name__+": "+str(exc)[:300]
        records.append(entry)
    result={"schema_version":"sgx-bank-counter-isins-v108",
            "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
            "official_historical_links_verified":sum(bool(x["record"]) for x in records),
            "official_master_complete":False,
            "financial_feed_modified":False,
            "ranking_eligible":False,"records":records}
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--output",required=True)
    args=a.parse_args()
    x=run(args.output)
    print("v108 official historical links:",x["official_historical_links_verified"],"of",len(x["records"]))
