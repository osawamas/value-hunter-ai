"""v106: SGX-hosted single issuer page evidence, not a stock-counter master."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://links.sgx.com/1.0.0/corporate-information/1637"
EXPECTED_NAME = "SINGAPORE EXCHANGE LIMITED"
EXPECTED_ISIN = "SG1J26887955"
KNOWN_SYMBOL = "S68"

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden+=1
        if tag in ("div","p","h1","h2","h3","br","td","tr","li","span"):
            self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag in ("script","style") and self.hidden:self.hidden-=1
        if tag in ("div","p","h1","h2","h3","td","tr","li","span"):
            self.parts.append(" ")
    def handle_data(self, value):
        if not self.hidden:self.parts.append(value)

def parse(raw):
    if not isinstance(raw, bytes) or not 100 <= len(raw) <= 2_000_000:
        raise ValueError("Invalid issuer page byte length")
    doc=Text();doc.feed(raw.decode("utf-8","replace"))
    plain=" ".join(" ".join(doc.parts).split())
    if not re.search(r"Basic Info\s+"+EXPECTED_NAME+r"\s+Full Company Name\s*:\s*"+EXPECTED_NAME+r"\b",plain,re.I):
        raise ValueError("SGX issuer page identity not found")
    isins=re.findall(r"ISIN Code\s*:\s*([A-Z0-9]{12})\b",plain,re.I)
    if isins != [EXPECTED_ISIN]:
        raise ValueError("Unique expected ISIN not found")
    if not re.search(r"LISTING\s+Listed on\s+\d{1,2}\s+\w+\s+\d{4}\s+on SGX Mainboard",plain,re.I):
        raise ValueError("Mainboard listing statement missing")
    boards=re.findall(r"LISTING BOARD\s+(MAINBOARD|CATALIST|GLOBAL LISTING BOARD)\b",plain,re.I)
    if boards != ["MAINBOARD"]:
        raise ValueError("Listing board missing or conflicting")
    stamps=re.findall(r"Information last updated on\s+(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*[AP]M)",plain,re.I)
    # SGX page uses month/day/year; display as original text, not a guessed timezone.
    if not stamps or len(set(stamps)) != 1:
        raise ValueError("Unique metadata update timestamp missing")
    datetime.strptime(stamps[0],"%m/%d/%Y %I:%M:%S %p")
    return {
        "status": "SGX_HOSTED_ISSUER_PAGE_CONTENT_MATCHED",
        "source_url": URL, "source_sha256":hashlib.sha256(raw).hexdigest(),
        "issuer_name": EXPECTED_NAME, "isin": EXPECTED_ISIN,
        "board": "MAINBOARD", "page_updated_local_text": stamps[0],
        "candidate_symbol":KNOWN_SYMBOL,
        "symbol_directly_observed_on_sgx_page":False,
        "symbol_to_isin_official_master_join_verified":False,
        "scope":"INDIVIDUAL_ISSUER_ONLY_NOT_FULL_MASTER",
        "eligible_for_financial_promotion":False,
        "eligible_for_ranking":False
    }

def fetch():
    req=Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 (issuer-evidence-research)",
                             "Accept":"text/html"})
    with urlopen(req,timeout=25) as response:
        if response.geturl() != URL:raise ValueError("SGX issuer page redirect")
        if "html" not in response.headers.get("Content-Type","").lower():
            raise ValueError("Issuer source is not HTML")
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("SGX issuer page oversized")
    return raw

def run(output,raw=None):
    result={"schema_version":"sgx-individual-issuer-evidence-v106",
            "fetched_at_utc":datetime.now(timezone.utc).isoformat(),
            "requested_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
    try:
        result["record"]=parse(fetch() if raw is None else raw)
        result["status"]=result["record"]["status"]
    except Exception as exc:
        result["error"]=type(exc).__name__+": "+str(exc)[:300]
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    a=p.parse_args();z=run(a.output)
    print("SGX v106",z["status"],z["error"])
    # Network unavailability is recorded as NOT_VERIFIED, not claimed success.
