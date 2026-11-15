#!/usr/bin/env python3
"""v293 reproducible SGX-owned October 2026 release acquisition.
Original SGXNet monthly attachment remains missing: this NEVER certifies
October monthly listing counts, complete master or a market-data license.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
import pathlib
import re
import urllib.request
from urllib.parse import urlparse

ROOT=pathlib.Path(__file__).resolve().parent.parent
URL="https://www.sgxgroup.com/media-centre/20261112-sgx-groups-derivatives-volume-hits-six-month-high-securities"
REFERENCE="SG261112OTHREO8V"  # third-party mirror identifier; not independently SGXNet certified
MAX_BYTES=2_000_000

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def inspect_html(raw):
    if not isinstance(raw,bytes) or len(raw)<100:raise ValueError("HTML absent or too small")
    p=VisibleText()
    p.feed(raw.decode("utf-8",errors="replace"))
    text=" ".join(" ".join(p.parts).split()).lower()
    checks={
      "sgx_group":bool(re.search(r"sgx\s+group",text)),
      "october_2026":bool(re.search(r"october\s+2026",text)) or ("12 november 2026" in text and "october" in text),
      "deluge": "deluge corporation" in text,
      "mi_material": "mi material holding" in text,
      "two_ipos":bool(re.search(r"two\s+(?:initial\s+share\s+offerings|ipos)",text)),
      "securities_turnover":("securities" in text and "turnover" in text),
      "headline":("derivatives volume hits six-month high" in text)
    }
    return {"checks":checks,"all_required_text_matched":all(checks.values()),
      "issuer_source_only":True,"sgxnet_original_attachment_fetched":False,
      "october_month_end_listings_verified":False,"ipo_trading_codes_verified":False,
      "investment_ranking_eligible":False}

def retrieve():
    body=b"";problem=None
    try:
        req=urllib.request.Request(URL,headers={
          "User-Agent":"VALUE-HUNTER-AI-issuer-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
          "Accept":"text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req,timeout=30) as reply:
            final=reply.geturl()
            target=urlparse(final)
            if(target.scheme!="https" or target.hostname!="www.sgxgroup.com" or target.path!=urlparse(URL).path):
                raise ValueError("Unexpected redirect outside official source")
            if "html" not in reply.headers.get("Content-Type","").lower():
                raise ValueError("Source response is not HTML")
            body=reply.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES:raise ValueError("Unexpected large response")
        checks=inspect_html(body)
    except (OSError,ValueError,TimeoutError,UnicodeError) as exc:
        problem=type(exc).__name__
        checks={"all_required_text_matched":False,
          "sgxnet_original_attachment_fetched":False,
          "october_month_end_listings_verified":False,
          "ipo_trading_codes_verified":False,"investment_ranking_eligible":False}
    report={
      "schema_version":"sgx-owned-oct26-release-live-replay-v293",
      "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_url":URL,
      "secondary_reported_sgxnet_reference":REFERENCE,
      "sgxnet_reference_independently_verified":False,
      "raw_html_bytes":len(body),
      "raw_html_sha256":hashlib.sha256(body).hexdigest() if body else None,
      "download_error_type":problem,"checks":checks,
      "monthly_statistics_original_pdf_sha256":None,
      "licensed_market_data":False,"ranking_eligible_count":0
    }
    out=ROOT/"build/research/sgx-october-issuer-live-v293.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("v293 "+("ISSUER_LIVE_TEXT_PASS" if checks["all_required_text_matched"] else "ISSUER_NOT_RECONCILED")+
          " bytes="+str(len(body))+" sha256="+str(report["raw_html_sha256"]))
    if not checks["all_required_text_matched"]:
        raise SystemExit(1)

if __name__=="__main__":retrieve()
