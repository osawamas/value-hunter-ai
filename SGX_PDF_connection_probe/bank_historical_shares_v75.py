"""Official historical issued/treasury shares for SGX banks O39 and U11.

As-of February 2026, not a verified November 2026 issued share count.
From the same 2025 annual issuer PDFs as audited banking statements, never
from a market quote; historical evidence only, not market cap/PER/PBR inputs.
"""
import argparse,hashlib,json,re
from pathlib import Path
from official_http_v57 import get_pdf
from bank_statements_probe_v66 import SOURCES

CONFIG={
 "O39":{"page":256,"date":"2026-02-25","gross":4501436229,
        "treasury":10523722,"net":4490912507},
 "U11":{"page":237,"date":"2026-02-23","gross":1666832191,
        "treasury":15243008,"net":1651589183},
}

def parse_pdf(symbol,raw):
 import fitz
 if symbol not in CONFIG:raise ValueError("Unsupported bank")
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
  raise ValueError("Issuer PDF content invalid")
 conf=CONFIG[symbol]
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)<conf["page"]:raise ValueError("Annual statement shareholding page absent")
  intro=" ".join(doc[i].get_text("text") for i in range(min(35,len(doc)))).lower()
  if not any(name.lower() in intro for name in SOURCES[symbol]["identity"]):
   raise ValueError("Wrong listed issuer identity")
  content=" ".join(doc[conf["page"]-1].get_text("text").split())
  date_label="25 February 2026" if symbol=="O39" else "23 February 2026"
  title="Shareholding Statistics" if symbol=="O39" else "Statistics of Shareholdings"
  if not re.search(re.escape(title)+r"\\s+as at\\s+"+re.escape(date_label),content,re.I):
   raise ValueError("Dated annual-shareholding table heading missing")
  if symbol=="O39":
   gross_match=re.findall(r"Number of issued shares \(including treasury shares\):\s*([\d,]+)",content,re.I)
   treasury_match=re.findall(r"Number of treasury shares held:\s*([\d,]+)",content,re.I)
   if len(gross_match)!=1 or len(treasury_match)!=1:
    raise ValueError("OCBC gross/treasury labels missing or duplicated")
   gross=int(gross_match[0].replace(",",""))
   treasury=int(treasury_match[0].replace(",",""))
   if not re.search(r"Number of subsidiary holdings held:\s*Nil",content,re.I):
    raise ValueError("OCBC subsidiary holdings require separate accounting")
   net=gross-treasury
   derivation="NET_DERIVED_GROSS_MINUS_TREASURY"
  else:
   net_matches=re.findall(r"Total\s+67,735\s+100\.00\s+([\d,]+)\s+100\.00",content,re.I)
   treasury_matches=re.findall(r"As at 23 February 2026, the Company had\s+([\d,]+)\s+treasury shares",content,re.I)
   if len(net_matches)!=1 or len(treasury_matches)!=1:
    raise ValueError("UOB net shareholding total/treasury table missing or duplicated")
   net=int(net_matches[0].replace(",",""))
   treasury=int(treasury_matches[0].replace(",",""))
   if not re.search(r"no subsidiary holdings",content,re.I):
    raise ValueError("UOB subsidiary holdings require separate accounting")
   gross=net+treasury
   derivation="GROSS_DERIVED_NET_PLUS_TREASURY"
  if (gross<=0 or treasury<0 or net<=0 or gross-treasury!=net or
      (gross,treasury,net)!=(conf["gross"],conf["treasury"],conf["net"])):
   raise ValueError("Issuer official historical shares regression mismatch")
  return {
   "symbol":symbol,"as_of_date":conf["date"],
   "gross_issued_shares":gross,
   "treasury_shares":treasury,
   "issued_excluding_treasury":net,
   "shares_count_basis":"issued_excluding_treasury",
   "derivation":derivation,
   "subsidiary_holdings":0,
   "source_pdf_page":conf["page"],
   "historical_only":True,
   "market_cap_or_ranking_eligible":False,
  }
 finally:doc.close()

def run(symbol,output,raw=None):
 record={"symbol":symbol,"status":"NOT_VERIFIED",
         "source_url":SOURCES[symbol]["url"],
         "pdf_sha256":None,"record":None,"error":None}
 try:
  data=get_pdf(SOURCES[symbol]["url"],max_bytes=75_000_000,timeout=90) if raw is None else raw
  record["pdf_sha256"]=hashlib.sha256(data).hexdigest()
  record["record"]=parse_pdf(symbol,data)
  record["status"]="ISSUER_HISTORICAL_TREASURY_ARITHMETIC_RECONCILED"
 except Exception as exc:
  record["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
 target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return record

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--symbol",choices=tuple(CONFIG),required=True)
 p.add_argument("--output",required=True);p.add_argument("--offline-pdf")
 a=p.parse_args(); r=run(a.symbol,a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
 print(a.symbol,r["status"],r["error"])
 raise SystemExit(0 if r["status"]=="ISSUER_HISTORICAL_TREASURY_ARITHMETIC_RECONCILED" else 1)
