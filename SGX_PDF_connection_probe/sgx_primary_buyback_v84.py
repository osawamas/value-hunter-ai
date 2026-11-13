"""v84: read original SGX daily buyback notice, strictly diagnostic-only.

An issuer SGXNet secondary mirror cannot satisfy this parser. It requires a
direct HTTPS SGX corporate-announcement URL, bank code/identity, reference,
purchase date and Section D post-purchase share counts. Counts are NEVER
promoted to live shares, PER, PBR or ranking by this probe.
"""
import argparse,hashlib,json,re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

ISSUER_NAMES={"U11":"UNITED OVERSEAS BANK LIMITED",
              "O39":"OVERSEA-CHINESE BANKING CORPORATION LIMITED",
              "D05":"DBS GROUP HOLDINGS LTD"}
OFFICIAL=re.compile(r"^/1\.0\.0/corporate-announcements/[A-Za-z0-9]+/?$")
REF=re.compile(r"SG\d{6}OTHR[A-Z0-9]+")

class VisibleText(HTMLParser):
 def __init__(self):
  super().__init__()
  self.parts=[]
  self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style"):self.skip+=1
  if tag in ("div","p","tr","td","th","h1","h2","h3","h4","br","li"):
   self.parts.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style") and self.skip:self.skip-=1
  if tag in ("div","p","tr","td","th","h1","h2","h3","h4","li"):
   self.parts.append(" ")
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)

def parse(symbol,url,body,reference,as_of_date):
 parsed=urlsplit(url)
 if (parsed.scheme!="https" or parsed.netloc!="links.sgx.com"
     or not OFFICIAL.fullmatch(parsed.path)
     or parsed.query or parsed.fragment or symbol not in ISSUER_NAMES):
  raise ValueError("Only original SGX corporate-announcement HTTP URL is accepted")
 if not REF.fullmatch(reference):
  raise ValueError("Invalid SGXNet announcement reference")
 if not re.fullmatch(r"2026-(0[1-9]|1[0-2])-[0-3][0-9]",as_of_date):
  raise ValueError("Unsupported purchase date")
 if not isinstance(body,bytes) or len(body)>2_000_000:
  raise ValueError("Official announcement HTML invalid size")
 html=body.decode("utf-8","replace")
 collector=VisibleText()
 collector.feed(html)
 text=" ".join(unescape("".join(collector.parts)).split())
 if len(text)<100:
  raise ValueError("SGX announcement content unavailable")
 if (ISSUER_NAMES[symbol].lower() not in text.lower()
     or reference not in text
     or "Share Buy Back" not in text
     or "Daily Share Buy-Back Notice" not in text):
  raise ValueError("Official issuer, notice type or reference not matched")
 d,m,y=as_of_date[8:10],as_of_date[5:7],as_of_date[:4]
 date=f"{d}/{m}/{y}"
 if not re.search(r"Date of Purchase\s+"+re.escape(date)+r"\b",text,re.I):
  raise ValueError("Official purchase date absent")
 if not re.search(r"Section D\b",text,re.I):
  raise ValueError("Official Section D missing")
 tail=re.split(r"Section D\b",text,flags=re.I)
 if len(tail)!=2:
  raise ValueError("Section D missing/ambiguous")
 tail=tail[1]
 def extract(label):
  matches=re.findall(re.escape(label)+r"\s*([0-9][0-9,]*)\b",tail,re.I)
  if len(matches)!=1:
   raise ValueError("Official Section D field absent or repeated: "+label)
  return int(matches[0].replace(",",""))
 net=extract("Number of issued shares excluding treasury shares after purchase")
 treasury=extract("Number of treasury shares held after purchase")
 if net<=0 or treasury<0:
  raise ValueError("Official shares invalid")
 return {"symbol":symbol,
         "status":"DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY",
         "reference":reference,"as_of_date":as_of_date,
         "issued_excluding_treasury":net,
         "treasury_shares":treasury,
         "issued_including_treasury_derived":net+treasury,
         "source_url":url,
         "primary_sgx_page_sha256":hashlib.sha256(body).hexdigest(),
         "not_proof_of_latest":True,
         "requires_additional_events_and_crosscheck":True,
         "valuation_eligible":False,"ranking_eligible":False}

def fetch(url):
 req=Request(url,headers={"User-Agent":"VALUE-HUNTER-AI/1.0 research-only","Accept":"text/html"})
 with urlopen(req,timeout=20) as response:
  if response.geturl()!=url:
   raise ValueError("Redirected official SGX URL not permitted")
  data=response.read(2_000_001)
 if len(data)>2_000_000:
  raise ValueError("SGX source page too large")
 return data

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--symbol",choices=tuple(ISSUER_NAMES),required=True)
 p.add_argument("--url",required=True)
 p.add_argument("--reference",required=True)
 p.add_argument("--date",required=True)
 p.add_argument("--output",required=True)
 p.add_argument("--offline-html")
 a=p.parse_args()
 record={"symbol":a.symbol,"status":"NOT_VERIFIED","source_url":a.url,"record":None,"error":None}
 try:
  body=Path(a.offline_html).read_bytes() if a.offline_html else fetch(a.url)
  record["record"]=parse(a.symbol,a.url,body,a.reference,a.date)
  record["status"]="DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY"
 except Exception as exc:
  record["error"]=f"{type(exc).__name__}: {str(exc)[:320]}"
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(record["status"],record["error"])
 raise SystemExit(0 if record["record"] else 1)
