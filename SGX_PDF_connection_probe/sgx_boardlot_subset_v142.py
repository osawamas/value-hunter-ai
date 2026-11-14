"""v142: historical SGX official 10-share board-lot subset is NOT an exchange-wide master."""
import argparse,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen

SOURCE="https://www.sgx.com/securities/trading"
EXPECTED={
"D05":("DBS Group Holdings Ltd","SGD"),
"G07":("Great Eastern Holdings Ltd","SGD"),
"H02":("Haw Par Corporation Ltd","SGD"),
"C07":("Jardine Cycle & Carriage Ltd","SGD"),
"J36":("Jardine Matheson Holdings Ltd","USD"),
"BN4":("Keppel Ltd","SGD"),
"O39":("Oversea-Chinese Banking Corporation Ltd","SGD"),
"K6S":("Prudential PLC","USD"),
"S68":("Singapore Exchange Limited","SGD"),
"U11":("United Overseas Bank Limited","SGD"),
"V03":("Venture Corporation Limited","SGD")
}
class TableParser(HTMLParser):
 def __init__(self):
  super().__init__();self.in_tr=False;self.in_td=False;self.current=[];self.chunk=[];self.rows=[];self.hidden=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.hidden+=1
  if tag=="tr":self.in_tr=True;self.current=[]
  if self.in_tr and tag in ("td","th"):self.in_td=True;self.chunk=[]
 def handle_data(self,data):
  if not self.hidden and self.in_td:self.chunk.append(data)
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.hidden:self.hidden-=1
  if tag in ("td","th") and self.in_td:
   self.current.append(" ".join(" ".join(self.chunk).split()));self.in_td=False
  if tag=="tr" and self.in_tr:
   self.rows.append(self.current);self.in_tr=False
def parse(raw):
 if not isinstance(raw,bytes) or len(raw)<300 or len(raw)>4_000_000:raise ValueError("Invalid SGX original")
 p=TableParser();p.feed(raw.decode("utf-8","replace"))
 visible=" ".join(raw.decode("utf-8","replace").split())
 if not re.search(r"5 October 2026",visible,re.I) or not re.search(r"reduced board lot",visible,re.I):
  raise ValueError("Original historical board-lot date absent")
 found={}
 for row in p.rows:
  if len(row)<3:continue
  name,code,currency=row[:3]
  if code in EXPECTED:
   if code in found:raise ValueError("Duplicate official stock code")
   if (name,currency)!=EXPECTED[code]:raise ValueError("Unexpected issuer name or trading currency "+code)
   found[code]={"symbol":code,"issuer":name,"traded_currency":currency,
                "board_lot_shares":10,"effective_date":"2026-10-05"}
 if set(found)!=set(EXPECTED):raise ValueError("Official 11 code table absent or incomplete")
 return {"schema_version":"sgx-historical-boardlot-code-subset-v142",
   "source_url":SOURCE,"html_sha256":hashlib.sha256(raw).hexdigest(),
   "announcement_effective_date":"2026-10-05",
   "official_historical_ticker_count":11,
   "subset_is_complete_current_sgx_master":False,
   "listing_active_as_of_today_confirmed":False,
   "current_boardlot_for_all_sgx_issuers_verified":False,
   "quote_prices_fetched":False,"ranking_eligible":False,
   "records":[found[k] for k in sorted(found)]}
def fetch():
 req=Request(SOURCE,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 public-history",
                           "Accept":"text/html"})
 with urlopen(req,timeout=25) as r:
  if r.geturl()!=SOURCE or "html" not in r.headers.get("Content-Type","").lower():
   raise ValueError("SGX page not HTML")
  data=r.read(4_000_001)
 return data

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args();out={"schema_version":"sgx-boardlot-subset-probe-v142","status":"NOT_VERIFIED",
                       "record":None,"error":None}
 try:out["record"]=parse(fetch());out["status"]="SGX_OFFICIAL_HISTORICAL_BOARDLOT_TABLE_VERIFIED"
 except Exception as e:
  out["error"]=type(e).__name__+": "+str(e)[:260]
  try:
   raw=fetch()
   html=raw.decode("utf-8","replace")
   out["response_diagnostics"]={
    "response_bytes":len(raw),"response_sha256":hashlib.sha256(raw).hexdigest(),
    "contains_2026_effective_date":"5 October 2026" in html,
    "has_securities_table_label":"Stock code" in html,
    "has_D05_label":bool(re.search(r"\\bD05\\b",html)),
    "has_loading_fallback":"loading" in html.lower()
   }
  except Exception as ex:
   out["response_diagnostics_error"]=type(ex).__name__+": "+str(ex)[:100]
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
