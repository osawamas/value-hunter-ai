"""v109: SGX 2026-11-13 ST Engineering buyback snapshot (historical only)."""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://links.sgx.com/1.0.0/corporate-announcements/4NRLOX68RVAQLTX7/e975f3ae39506c95439e92080a725fbbaa980e0196ddca2c946c55442faf6d92"
REF="SG261113OTHRPXGV"
ISIN="SG1F60858221"
SYMBOL="S63"

class Text(HTMLParser):
 def __init__(self):
  super().__init__();self.t=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("style","script"):self.hidden+=1
  if tag in ("div","span","p","h1","h2","h3","td","tr","li","br"):self.t.append(" ")
 def handle_endtag(self,tag):
  if tag in ("style","script") and self.hidden:self.hidden-=1
  if tag in ("div","span","p","h1","h2","h3","td","tr","li"):self.t.append(" ")
 def handle_data(self,v):
  if not self.hidden:self.t.append(v)

def unique(pattern,plain,field):
 matches=re.findall(pattern,plain,re.I)
 if len(matches)!=1:raise ValueError(field+" missing or ambiguous")
 return matches[0]

def parse(raw):
 if not isinstance(raw,bytes) or not 300<=len(raw)<=3_000_000:
  raise ValueError("Invalid SGX notice")
 h=Text();h.feed(raw.decode("utf-8","replace"))
 s=" ".join(" ".join(h.t).split())
 unique(r"Issuer\s*/\s*Manager\s+SINGAPORE TECHNOLOGIES ENGINEERING LTD\s+Securities\s+SINGAPORE TECH ENGINEERING LTD\s*-\s*"+ISIN+r"\s*-\s*"+SYMBOL+r"\b",s,"SGX issuer security")
 unique(r"Announcement Reference\s+"+REF+r"\b",s,"announcement reference")
 unique(r"Date\s*&\s*Time of Broadcast\s+13-Nov-2026\s+18:21:18\b",s,"broadcast time")
 unique(r"Date of Purchase\s*\|?\s*13/11/2026\b",s,"purchase date")
 bought=int(unique(r"Total Number of shares purchased\s*\|?\s*([0-9,]+)\b",s,"bought shares").replace(",",""))
 cancelled=int(unique(r"Number of shares cancelled\s*\|?\s*([0-9,]+)\b",s,"cancelled shares").replace(",",""))
 treasury_add=int(unique(r"Number of shares held as treasury shares\s*\|?\s*([0-9,]+)\b",s,"treasury acquired").replace(",",""))
 issued=int(unique(r"Number of issued shares excluding treasury shares after purchase\s*([0-9,]+)\b",s,"issued ex treasury").replace(",",""))
 treasury=int(unique(r"Number of treasury shares held after purchase\s*([0-9,]+)\b",s,"treasury outstanding").replace(",",""))
 if not (bought==500000 and cancelled==0 and treasury_add==500000
         and issued==3115847115 and treasury==6648082
         and bought==cancelled+treasury_add):
  raise ValueError("Actual SGX share count arithmetic/regression mismatch")
 return {"status":"SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT",
         "source_url":URL,"source_sha256":hashlib.sha256(raw).hexdigest(),
         "symbol":SYMBOL,"isin":ISIN,"reference":REF,
         "broadcast_sgt_text":"13-Nov-2026 18:21:18",
         "purchase_date":"2026-11-13","shares_purchased":bought,
         "shares_cancelled":cancelled,"purchased_as_treasury":treasury_add,
         "issued_excluding_treasury_after_purchase":issued,
         "treasury_shares_after_purchase":treasury,
         "dated_historical_snapshot_only":True,
         "verified_current_shares_at_newer_dates":False,
         "verified_trade_time_stock_quote":False,
         "allow_market_cap_or_per_pbr":False,
         "ranking_eligible":False}

def fetch():
 with urlopen(Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 primary-research","Accept":"text/html"}),timeout=25) as resp:
  if resp.geturl()!=URL or "html" not in resp.headers.get("Content-Type","").lower():
   raise ValueError("Unexpected SGX official HTML response")
  raw=resp.read(3_000_001)
 if len(raw)>3_000_000:raise ValueError("Oversized source")
 return raw

def run(output):
 out={"schema_version":"sgx-s63-buyback-original-v109",
      "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  out["record"]=parse(fetch());out["status"]=out["record"]["status"]
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:300]
 p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return out

if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",required=True)
 x=a.parse_args();r=run(x.output);print(r["status"],r["error"])
