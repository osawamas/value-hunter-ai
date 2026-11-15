#!/usr/bin/env python3
"""v260: bounded retrieval of issuer SECURITY identity pages from links.sgx.com.
Replays public issuer-announcement HTML only; does not fetch quotes or PDF attachments.
Never marks an issuer currently listed or an investor ranking eligible.
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent.parent
MAX_BYTES=1_500_000
SELECTED=("OILTEK INTERNATIONAL LIMITED","OLD CHANG KEE LTD.","OTS HOLDINGS LIMITED","OXLEY HOLDINGS LIMITED")
def source_rows():
    a=json.loads((ROOT/"docs/data/sgx-official-issuer-code-filings-v255.json").read_text())
    b=json.loads((ROOT/"docs/data/sgx-net-eleven-codes-v256.json").read_text())
    items=[]
    for obj in a["records"]:
        if obj["issuer_name"] in SELECTED:
            items.append(dict(name=obj["issuer_name"],code=obj["trading_code"],
                isin=obj["isin"],reference=obj["announcement_ref"],url=obj["source_url"]))
    for obj in b["records"]:
        if obj["issuer_name"] in SELECTED:
            items.append(dict(name=obj["issuer_name"],code=obj["code"],
                isin=obj["isin"],reference=obj["filing_reference"],url=obj["source_url"]))
    if len(items)!=4 or {x["name"] for x in items}!=set(SELECTED):
        raise ValueError("Source fixture set is incomplete")
    return sorted(items,key=lambda x:x["name"])
def validate_url(url):
    v=urllib.parse.urlsplit(url)
    if(v.scheme!="https" or v.hostname!="links.sgx.com" or v.username or v.password
       or v.fragment or v.query or v.port is not None
       or not re.fullmatch(r"/1\.0\.0/corporate-announcements/[A-Z0-9]{16}(?:/[0-9a-f]{64})?/?",v.path)):
        raise ValueError("Unsafe/unsupported SGX announcement address")
    return url
def clean_text(raw):
    # Source content is never stored, published or redisplayed; this is for identity tests only.
    page=raw.decode("utf-8",errors="replace")
    page=re.sub(r"<(?:script|style)\b[^>]*>[\s\S]*?</(?:script|style)>"," ",page,flags=re.I)
    page=re.sub(r"<[^>]+>"," ",page)
    return re.sub(r"\s+"," ",html.unescape(page)).upper()
def inspect(row,response_bytes,status=200,content_type="text/html"):
    text=clean_text(response_bytes) if "html" in content_type.lower() else ""
    matches={
        "issuer_name_present":row["name"].upper() in text,
        "isin_present":row["isin"].upper() in text,
        "code_present":bool(re.search(r"(?<![A-Z0-9])"+re.escape(row["code"].upper())+r"(?![A-Z0-9])",text)),
        "announcement_reference_present":row["reference"].upper() in text,
        "issuer_securities_heading_present":"ISSUER" in text and "SECURITIES" in text,
    }
    fully=bool(status==200 and all(matches.values()))
    return {
        "issuer":row["name"],"security_code":row["code"],"isin":row["isin"],
        "source_url":row["url"],"announcement_reference":row["reference"],
        "http_status":status,"content_type":content_type,
        "download_bytes":len(response_bytes),
        "download_sha256":hashlib.sha256(response_bytes).hexdigest() if response_bytes else None,
        "individual_text_checks":matches,
        "original_body_identity_verified":fully,
        "observation_status":"MATCHED_OFFICIAL_BODY" if fully else "NOT_VERIFIED",
        "current_listing_verified":False,"live_quote_verified":False,
        "financial_ranking_eligible":False,
    }
def fetch(row,opener=urllib.request.urlopen):
    validate_url(row["url"])
    req=urllib.request.Request(row["url"],headers={
        "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
        "Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"})
    try:
        with opener(req,timeout=18) as response:
            length=response.read(MAX_BYTES+1)
            if len(length)>MAX_BYTES:raise ValueError("Issuer HTML exceeds safety bound")
            return inspect(row,length,response.status,response.headers.get("Content-Type",""))
    except (urllib.error.URLError,TimeoutError,ValueError,OSError) as error:
        return {
            "issuer":row["name"],"security_code":row["code"],
            "isin":row["isin"],"source_url":row["url"],
            "announcement_reference":row["reference"],
            "observation_status":"FETCH_UNAVAILABLE",
            "error_type":type(error).__name__,
            "original_body_identity_verified":False,
            "current_listing_verified":False,"live_quote_verified":False,
            "financial_ranking_eligible":False,
        }
def main():
    entries=[]
    for i,row in enumerate(source_rows()):
        if i:time.sleep(1.0)
        entries.append(fetch(row))
        print(row["code"]+": "+entries[-1]["observation_status"],flush=True)
    report={
        "schema_version":"sgx-net-direct-original-page-replay-v260",
        "observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "sample_only":True,"sample_count":len(entries),
        "original_html_verified_count":sum(x["original_body_identity_verified"] for x in entries),
        "not_verified_count":sum(not x["original_body_identity_verified"] for x in entries),
        "current_full_security_master_verified":False,
        "license_for_quote_redistribution_verified":False,
        "ranking_eligible_count":0,
        "entries":entries
    }
    output=ROOT/"build/research/sgx-original-issuer-html-v260.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(f"v260 PROVENANCE: {report['original_html_verified_count']}/{len(entries)} original HTML bodies fully confirmed; unverified is NOT promoted.")
if __name__=="__main__":main()
