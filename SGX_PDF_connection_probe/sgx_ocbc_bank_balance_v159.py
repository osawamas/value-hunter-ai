"""v159: OCBC 2026 Q3 bank-balance sheet selected items from SGX primary PDF.

Historical issuer interim bank figures, not a full audited balance sheet, and
not proof of current shares or share-class-specific PBR denominator.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

NAME="OCBC_3Q26_Results_Press_Release.pdf"
ITEMS={
 "ordinary_equity":("Ordinary equity",60899),
 "equity_attributable_to_bank_equity_holders":("Equity attributable to equity holders of the Bank",63347),
 "total_assets":("Total assets",731689),
 "net_customer_loans":("Net loans to customers",366929),
 "deposits_nonbank_customers":("Deposits of non-bank customers",461462)
}
def read_row(lines,label,expected):
 idx=[i for i,x in enumerate(lines) if x.strip()==label]
 if len(idx)!=1:raise ValueError("Missing or ambiguous bank balance line: "+label)
 i=idx[0]
 if i+1>=len(lines) or lines[i+1].strip()!=f"{expected:,}":
  raise ValueError("Bank balance figure not in expected current-period column: "+label)
 return {"sgd_millions":expected,"source_line":i+1}

def extract(raw,manifest):
 if manifest.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED":
  raise ValueError("Manifest not verified")
 rec=[x for x in manifest.get("record",{}).get("records",[]) if x.get("filename")==NAME]
 if len(rec)!=1:raise ValueError("Source not unique")
 origin=rec[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=origin["sha256"]:
  raise ValueError("PDF content hash disagrees with actual SGX source")
 import fitz
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  if len(doc)!=origin["page_count"]:raise ValueError("Source page count differs")
  text=doc[7].get_text("text")
  lines=[" ".join(x.split()) for x in text.splitlines() if x.strip()]
  whole=" ".join(lines)
  if "Selected Balance Sheet Items" not in whole or "3Q26" not in whole:
   raise ValueError("Not actual OCBC Q3 selected bank balance statement")
  values={}
  for key,(label,expected) in ITEMS.items():
   values[key]=read_row(lines,label,expected)
 finally:doc.close()
 total=values["equity_attributable_to_bank_equity_holders"]["sgd_millions"]
 ordinary=values["ordinary_equity"]["sgd_millions"]
 if ordinary>total or ordinary<=0:raise ValueError("Ordinary equity exceeds shareholder attributable equity")
 return {"schema_version":"sgx-ocbc-q3-bank-balance-selected-v159",
  "symbol":"O39","period_end_date":"2026-09-30","unit":"SGD_millions",
  "official_source_pdf_url":origin["official_sgx_original_url"],
  "official_source_pdf_sha256":origin["sha256"],
  "pdf_page":8,"selected_bank_items":values,
  "attributable_equity_less_ordinary_equity":total-ordinary,
  "difference_is_not_identified_as_noncontrolling_interest":True,
  "bank_ordinary_equity_not_assumed_group_equity":True,
  "not_full_audited_bank_statement":True,
  "independent_third_party_numbers_verified":False,
  "current_treasury_adjusted_shares_verified":False,
  "current_sgx_quote_verified":False,
  "pbr_eligible":False,"ranking_eligible":False}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--manifest",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 manifest=json.loads(Path(a.manifest).read_text())
 out={"schema_version":"sgx-ocbc-q3-balance-probe-v159","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  origin=next(x for x in manifest["record"]["records"] if x["filename"]==NAME)
  out["record"]=extract(fetch_pdf(origin["official_sgx_original_url"]),manifest)
  out["status"]="OCBC_Q3_PRIMARY_BANK_BALANCE_ROWS_PARSED"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:270]
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
