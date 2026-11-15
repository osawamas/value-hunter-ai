#!/usr/bin/env python3
"""v284 official SGXNet UOB 12-Nov-2026 share buyback source replay.
Verify exact issuer, SGX security identifier and dated share count. The 13-Nov
notice remains separate/unverified and is NEVER treated as confirmed.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import urllib.error
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent.parent
SGX_URL=("https://links.sgx.com/1.0.0/corporate-announcements/"
 "MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d")
spec=importlib.util.spec_from_file_location("sgxhtml",ROOT/"scripts/replay-sgx-issuer-html-v260.py")
html_probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(html_probe)
EXPECTED={
 "issuer":"UNITED OVERSEAS BANK LIMITED",
 "isin":"SG1M31001969","code":"U11","reference":"SG261112OTHRSYPK",
 "purchase_date":"12/11/2026",
 "purchased":34000,"cancelled":34000,
 "shares_ex_treasury_after":1646711591,"treasury_after":14548000
}
def check_body(body):
    cleaned=html_probe.clean_text(body)
    essential=(
     EXPECTED["issuer"] in cleaned,
     EXPECTED["isin"] in cleaned,
     bool(re.search(r"(?<![A-Z0-9])U11(?![A-Z0-9])",cleaned)),
     EXPECTED["reference"] in cleaned,
     "ISSUER" in cleaned and "SECURITIES" in cleaned,
     "12-NOV-2026" in cleaned,
     EXPECTED["purchase_date"] in cleaned,
     "SHARE BUY-BACK" in cleaned,
    )
    # Validate quantities only within text adjacent to the actual SGXNet
    # notice's labelled fields, not accidental occurrence elsewhere in HTML.
    labelled={
      "purchased":r"TOTAL NUMBER OF SHARES PURCHASED\s*34,000\b",
      "cancelled":r"NUMBER OF SHARES CANCELLED\s*34,000\b",
      "shares_ex_treasury_after":r"NUMBER OF ISSUED SHARES EXCLUDING TREASURY SHARES AFTER PURCHASE\s*1,646,711,591\b",
      "treasury_after":r"NUMBER OF TREASURY SHARES HELD AFTER PURCHASE\s*14,548,000\b"
    }
    found={k:bool(re.search(pattern,cleaned)) for k,pattern in labelled.items()}
    matched=all(essential) and all(found.values())
    return {"original_document_identity_matched":all(essential),
      "numbers_labelled_match":found,"all_original_labels_matched":matched,
      "shares_ex_treasury_after":EXPECTED["shares_ex_treasury_after"] if matched else None,
      "treasury_after":EXPECTED["treasury_after"] if matched else None,
      "fully_original_verified":matched,
      "latest_2026_11_13_original_verified":False,
      "ranking_eligible":False}
def main():
    html_probe.validate_url(SGX_URL)
    status="UNAVAILABLE"
    body=b""
    try:
        req=urllib.request.Request(SGX_URL,headers={
         "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
         "Accept":"text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req,timeout=20) as response:
            if response.geturl()!=SGX_URL:raise ValueError("SGX URL redirected")
            if "html" not in response.headers.get("Content-Type","").lower():raise ValueError("Not SGX HTML")
            body=response.read(1500001)
            if len(body)>1500000:raise ValueError("SGX response too large")
            checked=check_body(body)
            status="VERIFIED_2026_11_12_ISSUER_AND_SHARE_COUNT" if checked["fully_original_verified"] else "BODY_MISMATCH"
    except (OSError,urllib.error.URLError,ValueError,TimeoutError) as ex:
        checked={"fully_original_verified":False,"original_document_identity_matched":False,
          "numbers_labelled_match":{},"all_original_labels_matched":False,
          "latest_2026_11_13_original_verified":False,"ranking_eligible":False,
          "fetch_error_class":type(ex).__name__}
    result={
      "schema_version":"uob-12nov-original-share-count-v284",
      "captured_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "original_sgxnet_url":SGX_URL,"announcement_ref":EXPECTED["reference"],
      "issuer_code":"U11","isin":EXPECTED["isin"],
      "original_html_sha256":hashlib.sha256(body).hexdigest() if body else None,
      "original_html_bytes":len(body),
      "source_date":"2026-11-12",
      "last_notice_nov13_original_verified":False,
      "current_share_count_verified":False,"current_quote_verified":False,
      "ranking_eligible_count":0,"observation_status":status,"observed":checked
    }
    out=ROOT/"build/research/uob-12nov-share-original-v284.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("v284 "+status+" body_bytes="+str(len(body))+" sha_available="+str(bool(body)))
if __name__=="__main__":main()
