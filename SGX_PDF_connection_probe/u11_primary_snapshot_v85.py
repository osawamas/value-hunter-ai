"""v85: one known ORIGINAL SGX UOB buyback filing, diagnostic only.

This 7-Sep-2026 event is *not* the 30-Sep-2026 secondary source and is
not the latest filing. Never update current shares/price/PER/PBR/ranking.
"""
import argparse,json
from pathlib import Path
from sgx_primary_buyback_v84 import parse,fetch

URL="https://links.sgx.com/1.0.0/corporate-announcements/XR54CRHWN0U287GV/"
REF="SG260907OTHRJM0S"
DATE="2026-09-07"

def run(path,raw=None):
 out={"symbol":"U11","status":"NOT_VERIFIED","source_url":URL,"record":None,"error":None}
 try:
  content=fetch(URL) if raw is None else raw
  # Bounded text diagnostic: official SGX tables can differ from fixtures.
  from sgx_primary_buyback_v84 import VisibleText
  from html import unescape
  view=VisibleText();view.feed(content.decode("utf-8","replace"))
  flat=" ".join(unescape("".join(view.parts)).split())
  for term in ("Section D","Number of issued shares excluding treasury shares after purchase",
               "Number of treasury shares held after purchase"):
   pos=flat.lower().find(term.lower())
   print("PRIMARY_HTML_FIELD",term,"PRESENT" if pos>=0 else "ABSENT",
         flat[max(0,pos-40):pos+185] if pos>=0 else "")
  row=parse("U11",URL,content,REF,DATE)
  if (row["issued_excluding_treasury"]!=1648956591
      or row["treasury_shares"]!=14160900
      or row["issued_including_treasury_derived"]!=1663117491):
   raise ValueError("Actual SGX original Section D figures changed")
  out["record"]=row
  out["status"]="OFFICIAL_SGX_U11_2026_09_07_SECTION_D_VERIFIED_DIAGNOSTIC"
 except Exception as exc:
  out["error"]=f"{type(exc).__name__}: {str(exc)[:350]}"
 target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True)
 a=p.parse_args()
 res=run(a.output)
 print(res["status"],res["error"])
 raise SystemExit(0 if res["record"] else 1)
