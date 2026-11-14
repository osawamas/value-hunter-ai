"""v122: direct SGX 10 June 2026 Genting buyback source for original share basis.

Source proves a dated, treasury-adjusted count on June 10, not a June 30
or current as-of share count. No price/share valuation promotion.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://links.sgx.com/1.0.0/corporate-announcements/CHP29KEV0YJ4ZBNY/"
ISIN="SGXE21576413"
REF="SG260610OTHRU53S"

class Visible(HTMLParser):
 def __init__(self):
  super().__init__();self.bits=[];self.hidden=0
 def handle_starttag(self,t,attrs):
  if t in ("script","style"):self.hidden+=1
  if t in ("div","p","td","tr","span","h1","h2","h3","br","li"):self.bits.append(" ")
 def handle_endtag(self,t):
  if t in ("script","style") and self.hidden:self.hidden-=1
  if t in ("div","p","td","tr","span","h1","h2","h3","li"):self.bits.append(" ")
 def handle_data(self,s):
  if not self.hidden:self.bits.append(s)
def parse(raw):
 if not isinstance(raw,bytes) or not 300<len(raw)<3_000_000:
  raise ValueError("Invalid SGX original")
 v=Visible();v.feed(raw.decode("utf-8","replace"))
 text=" ".join(" ".join(v.bits).split())
 def must(p,label):
  matches=re.findall(p,text,re.I)
  if len(matches)!=1:raise ValueError(label+" is missing/duplicated")
  return matches[0]
 must(r"Issuer\s*/\s*Manager\s+GENTING SINGAPORE LIMITED\s+Securities\s+GENTING SINGAPORE LIMITED\s*-\s*"+ISIN+r"\s*-\s*G13\b","issuer/ISIN/symbol")
 must(r"Announcement Reference\s+"+REF+r"\b","reference")
 must(r"Date\s*&\s*Time of Broadcast\s+10-Jun-2026\s+17:55:09\b","broadcast")
 must(r"Date of Purchase\s*10/06/2026\b","purchase date")
 bought=int(must(r"Total Number of shares purchased\s*([0-9,]+)\b","purchased").replace(",",""))
 canceled=int(must(r"Number of shares cancelled\s*([0-9,]+)\b","canceled").replace(",",""))
 acquired=int(must(r"Number of shares held as treasury shares\s*([0-9,]+)\b","treasury acquired").replace(",",""))
 issued=int(must(r"Number of issued shares excluding treasury shares after purchase\s*([0-9,]+)\b","issued ex treasury").replace(",",""))
 treasury=int(must(r"Number of treasury shares held after purchase\s*([0-9,]+)\b","treasury held").replace(",",""))
 if (bought,canceled,acquired,issued,treasury)!=(2000000,0,2000000,12063642274,30384550):
  raise ValueError("SGX original share counts mismatch expected 2026-06-10")
 return {"status":"SGX_G13_PRIMARY_JUNE10_BUYBACK_SHARE_SNAPSHOT",
   "symbol":"G13","isin":ISIN,"reference":REF,
   "source_url":URL,"html_sha256":hashlib.sha256(raw).hexdigest(),
   "purchase_date":"2026-06-10","broadcast_sgt_text":"10-Jun-2026 17:55:09",
   "shares_bought":bought,"shares_cancelled":canceled,
   "shares_added_to_treasury":acquired,
   "issued_excluding_treasury_after_purchase":issued,
   "treasury_shares_after_purchase":treasury,
   "proof_applies_only_to_june_10":True,
   "june_30_shares_independently_confirmed":False,
   "current_shares_verified":False,
   "quote_or_valuation_verified":False,"ranking_eligible":False}
def fetch():
 with urlopen(Request(URL,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 official-evidence",
                                   "Accept":"text/html"}),timeout=25) as r:
  if r.geturl()!=URL or "html" not in r.headers.get("Content-Type","").lower():
   raise ValueError("Wrong official source")
  raw=r.read(3_000_001)
 if len(raw)>3_000_000:raise ValueError("Oversized source")
 return raw
def run(path):
 z={"schema_version":"sgx-g13-buyback-share-basis-v122",
    "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
    "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  z["record"]=parse(fetch());z["status"]=z["record"]["status"]
 except Exception as e:z["error"]=type(e).__name__+": "+str(e)[:300]
 out=Path(path);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(z,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return z
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",required=True)
 p=a.parse_args();r=run(p.output);print(r["status"],r["error"])
