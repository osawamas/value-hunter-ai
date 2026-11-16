"""v109: SGX 2026-11-13 ST Engineering buyback snapshot (historical only)."""
import argparse,hashlib,json,re
from datetime import datetime,timedelta,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
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

def validate_source_url(url):
 u=urlsplit(url)
 if (u.scheme!="https" or u.netloc!="links.sgx.com" or u.query or u.fragment
     or not re.fullmatch(r"/1\.0\.0/corporate-announcements/[A-Z0-9]+(?:/[a-f0-9]{64})?/?",u.path)):
  raise ValueError("Expected an official SGXNet announcement URL")

def parse_notice(raw,url):
 validate_source_url(url)
 if not isinstance(raw,bytes) or not 300<=len(raw)<=3_000_000:
  raise ValueError("Invalid SGX notice")
 h=Text();h.feed(raw.decode("utf-8","replace"))
 s=" ".join(" ".join(h.t).split())
 unique(r"Issuer\s*/\s*Manager\s+SINGAPORE TECHNOLOGIES ENGINEERING LTD\s+Securities\s+SINGAPORE TECH ENGINEERING LTD\s*-\s*"+ISIN+r"\s*-\s*"+SYMBOL+r"\b",s,"SGX issuer security")
 unique(r"Announcement Title\s+Share Buy Back - Daily Share Buy-Back Notice\b",s,"announcement type")
 reference=unique(r"Announcement Reference\s+(SG\d{6}OTHR[A-Z0-9]+)\b",s,"announcement reference")
 broadcast_text=unique(r"Date\s*&\s*Time of Broadcast\s+(\d{2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2})\b",s,"broadcast time")
 broadcast=datetime.strptime(broadcast_text,"%d-%b-%Y %H:%M:%S")
 purchase=datetime.strptime(unique(r"Date of Purchase\s*\|?\s*(\d{2}/\d{2}/\d{4})\b",s,"purchase date"),"%d/%m/%Y").date()
 status=unique(r"Status\s+(New|Replacement)\s+Announcement Sub Title\b",s,"announcement status")
 reference_day=datetime.strptime(reference[2:8],"%y%m%d").date()
 if (not purchase<=reference_day<=broadcast.date()
     or (status.casefold()=="new" and reference_day!=broadcast.date())):
  raise ValueError("SGX purchase date, broadcast date or reference is inconsistent")
 bought=int(unique(r"Total Number of shares purchased\s*\|?\s*([0-9,]+)\b",s,"bought shares").replace(",",""))
 cancelled=int(unique(r"Number of shares cancelled\s*\|?\s*([0-9,]+)\b",s,"cancelled shares").replace(",",""))
 treasury_add=int(unique(r"Number of shares held as treasury shares\s*\|?\s*([0-9,]+)\b",s,"treasury acquired").replace(",",""))
 issued=int(unique(r"Number of issued shares excluding treasury shares after purchase\s*([0-9,]+)\b",s,"issued ex treasury").replace(",",""))
 treasury=int(unique(r"Number of treasury shares held after purchase\s*([0-9,]+)\b",s,"treasury outstanding").replace(",",""))
 if bought<=0 or bought!=cancelled+treasury_add or issued<=0 or treasury<treasury_add:
  raise ValueError("SGX share count arithmetic mismatch")
 return {"status":"SGX_PRIMARY_BUYBACK_DATED_SNAPSHOT",
         "source_url":url,"source_sha256":hashlib.sha256(raw).hexdigest(),
         "symbol":SYMBOL,"isin":ISIN,"reference":reference,"announcement_status":status,
         "broadcast_sgt_text":broadcast_text,
         "purchase_date":purchase.isoformat(),"shares_purchased":bought,
         "shares_cancelled":cancelled,"purchased_as_treasury":treasury_add,
         "issued_excluding_treasury_after_purchase":issued,
         "treasury_shares_after_purchase":treasury,
         "dated_historical_snapshot_only":True,
         "verified_current_shares_at_newer_dates":False,
         "verified_trade_time_stock_quote":False,
         "allow_market_cap_or_per_pbr":False,
         "ranking_eligible":False}

def parse(raw):
 notice=parse_notice(raw,URL)
 fields=("reference","broadcast_sgt_text","purchase_date","shares_purchased","shares_cancelled",
         "purchased_as_treasury","issued_excluding_treasury_after_purchase","treasury_shares_after_purchase")
 if tuple(notice[field] for field in fields)!=(REF,"13-Nov-2026 18:21:18","2026-11-13",500000,0,500000,3115847115,6648082):
  raise ValueError("Actual SGX share count arithmetic/regression mismatch")
 notice["status"]="SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT"
 return notice

def fetch(url=URL):
 validate_source_url(url)
 with urlopen(Request(url,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 primary-research","Accept":"text/html"}),timeout=25) as resp:
  if resp.geturl().rstrip("/")!=url.rstrip("/") or "html" not in resp.headers.get("Content-Type","").lower():
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
 a.add_argument("--url",help="Read a dated S63 notice from the official SGXNet archive")
 x=a.parse_args()
 if x.url is None:
  r=run(x.output);print(r["status"],r["error"])
 else:
  try:
   notice=parse_notice(fetch(x.url),x.url)
   broadcast=datetime.strptime(notice["broadcast_sgt_text"],"%d-%b-%Y %H:%M:%S")
   notice["broadcast_at_sgt"]=broadcast.replace(tzinfo=timezone(timedelta(hours=8))).isoformat()
   payload=json.dumps(notice,ensure_ascii=False,indent=2)
   if x.output=="-":
    print(payload)
   else:
    Path(x.output).write_text(payload+"\n",encoding="utf-8")
  except (OSError,ValueError) as exc:
   a.exit(1,f"S63 notice could not be verified: {exc}\n")
