#!/usr/bin/env python3
"""v275: one bounded SGX official trading-page replay of a precisely dated 11-security board-lot table.
No market quotations collected, stored or redistributed. Current listing status NOT inferred.
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
URL="https://www.sgx.com/securities/trading"
MAX_BODY=2_000_000

class TableRows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tr=False;self.in_cell=False;self.cells=[];self.cell_parts=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=="tr":self.tr=True;self.cells=[]
        elif tag in ("td","th") and self.tr:
            self.in_cell=True;self.cell_parts=[]
    def handle_data(self,data):
        if self.tr and self.in_cell:self.cell_parts.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.tr and self.in_cell:
            self.cells.append(" ".join(" ".join(self.cell_parts).split()))
            self.in_cell=False;self.cell_parts=[]
        elif tag=="tr" and self.tr:
            if self.cells:self.rows.append(self.cells[:])
            self.tr=False;self.cells=[];self.in_cell=False

def expected():
    f=json.loads((ROOT/"docs/data/sgx-official-batch-seed-v196.json").read_text())
    if(f.get("source_url")!=URL or f.get("schema_version")!="sgx-official-first-batch-board-lot-v196" or
       f.get("official_full_security_master_obtained") is not False or
       len(f.get("rows",[]))!=11 or f.get("ranking_eligible_count")!=0):
        raise ValueError("Official static source fixture altered")
    return f["rows"]

def verify(body,rows):
    parser=TableRows()
    parser.feed(body.decode("utf-8",errors="replace"))
    result=[]
    used=set()
    for x in rows:
        if(x.get("eligible_for_valuation") is not False or
           x.get("provenance")!="OFFICIAL_SGX_TRADING_PAGE_STATIC_BATCH" or
           x.get("board_lot_shares")!=10 or x.get("effective_date")!="2026-10-05"):
            raise ValueError("SGX static source row violated source policy")
        # A row must hold the exact company, ticker and traded currency in
        # adjacent cells. Never accept accidental symbols elsewhere on the page.
        found=[i for i,cols in enumerate(parser.rows) if len(cols)>=3 and
               any(cols[j]==x["name"] and cols[j+1]==x["symbol"] and
                   cols[j+2]==x["trading_currency"] for j in range(len(cols)-2))]
        if len(found)>1 or (found and found[0] in used):
            raise ValueError("Ambiguous official trading page row")
        if found:used.add(found[0])
        result.append({"symbol":x["symbol"],"name":x["name"],
          "currency":x["trading_currency"],"board_lot":10,
          "exact_table_row_verified":len(found)==1,
          "current_listed_status_verified":False,"live_price_licensed":False,
          "ranking_eligible":False})
    return result

def replay():
    request=urllib.request.Request(URL,headers={
       "User-Agent":"VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
       "Accept":"text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(request,timeout=25) as response:
            if response.geturl()!=URL:raise ValueError("Unexpected redirect")
            body=response.read(MAX_BODY+1)
            if len(body)>MAX_BODY:raise ValueError("Excessive SGX page response")
            content_type=response.headers.get("Content-Type","")
            if not content_type.lower().startswith("text/html"):raise ValueError("Not HTML")
            matched=verify(body,expected())
            status="ELEVEN_ROW_EXACT_MATCH" if all(x["exact_table_row_verified"] for x in matched) else "PARTIAL_TABLE_MATCH"
            digest=hashlib.sha256(body).hexdigest()
            byte_length=len(body)
    except (OSError,TimeoutError,ValueError,urllib.error.URLError) as error:
        matched=[{"symbol":x["symbol"],"exact_table_row_verified":False,
            "ranking_eligible":False} for x in expected()]
        status="NOT_VERIFIED_"+type(error).__name__
        digest=None;byte_length=0
    report={"schema_version":"sgx-trading-original-eleven-html-v275",
      "source_url":URL,"observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_scope":"OCT_5_2026_REDUCED_BOARD_LOT_11_ONLY",
      "http_source_body_sha256":digest,"http_source_body_bytes":byte_length,
      "status":status,"original_exact_row_matches":sum(x["exact_table_row_verified"] for x in matched),
      "scope_count":11,"original_body_stored":False,
      "official_complete_sgx_master":False,"all_active_current_listing_verified":False,
      "market_quote_redisplay_licensed":False,"ranking_eligible_count":0,
      "records":matched}
    out=ROOT/"build/research/sgx-trading-original-eleven-v275.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(f"v275 SGX OFFICIAL TRADING original exact table: {report['original_exact_row_matches']}/11; status={status}")
if __name__=="__main__":replay()
