"""v148: two original OCBC issuer PDF presentations checked for same 3Q rounded profit.

Both originate from OCBC: same-issuer corroboration, NOT independent
third-party earnings assurance or a complete SGX bank financial statement.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf

HIGHLIGHTS="OCBC_3Q26_Results_Highlights.pdf"
def compare(pdfs,profit,pdf):
 if (pdfs.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or
     pdfs.get("record",{}).get("schema_version")!="sgx-ocbc-q3-pdf-originals-v145" or
     profit.get("status")!="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED" or
     profit.get("record",{}).get("schema_version")!="sgx-ocbc-3q26-official-bank-results-v146"):
  raise ValueError("Prior two primary artifacts are missing")
 x=profit["record"]
 matches=[r for r in pdfs["record"]["records"] if r.get("filename")==HIGHLIGHTS]
 if len(matches)!=1:raise ValueError("Highlights original absent")
 source=matches[0]
 if not isinstance(pdf,bytes) or not pdf.startswith(b"%PDF") or hashlib.sha256(pdf).hexdigest()!=source["sha256"]:
  raise ValueError("Highlights PDF differs from v145 original SHA")
 import fitz
 doc=fitz.open(stream=pdf,filetype="pdf")
 try:pages=[p.get_text("text") for p in doc]
 finally:doc.close()
 full=" ".join(" ".join(pages).split()).lower()
 if "ocbc" not in full or not re.search(r"3q26",full):
  raise ValueError("OCBC 3Q26 identity missing")
 if not re.search(r"(?:s\$|sgd)?\s*2\.04\s*b",full,re.I):
  raise ValueError("No uniquely matched rounded 3Q 2.04 billion profit")
 if not re.search(r"(?:\+|up\s*)\s*3\s*%",full):
  raise ValueError("Reported group profit increase not identified")
 if x.get("group_net_profit_3q26_sgd_billion_reported")!="2.04" or x.get("group_net_profit_3q26_yoy_pct_reported")!=3:
  raise ValueError("SGX press release disagrees with highlights")
 if source["official_sgx_original_url"]==x["original_sgx_press_release_url"] or source["sha256"]==x["original_sgx_pdf_sha256"]:
  raise ValueError("Must be distinct authentic OCBC issuer documents")
 return {
  "schema_version":"sgx-ocbc-q3-issuer-two-pdf-crosscheck-v148",
  "symbol":"O39","period_end_date":"2026-09-30",
  "reported_group_net_profit_3q26_sgd_billion":"2.04",
  "reported_group_net_profit_yoy_pct":3,
  "original_press_release_pdf_sha256":x["original_sgx_pdf_sha256"],
  "original_highlights_pdf_sha256":source["sha256"],
  "different_issuer_document_hashes_confirmed":True,
  "same_issuer_rounded_q3_profit_consistency":True,
  "independent_third_party_reperformance":False,
  "independently_audited_interim_profit":False,
  "annualised_per_or_pbr_permitted":False,
  "live_quote_or_shares_verified":False,
  "ranking_eligible":False
 }

def main():
 p=argparse.ArgumentParser()
 for name in ("pdfs","profit","output"):p.add_argument("--"+name,required=True)
 a=p.parse_args()
 manifest=json.loads(Path(a.pdfs).read_text());profit=json.loads(Path(a.profit).read_text())
 out={"schema_version":"sgx-ocbc-q3-crosscheck-probe-v148","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  item=next(x for x in manifest["record"]["records"] if x["filename"]==HIGHLIGHTS)
  out["record"]=compare(manifest,profit,fetch_pdf(item["official_sgx_original_url"]))
  out["status"]="OCBC_3Q26_TWO_ISSUER_PDFS_ROUNDED_PROFIT_MATCH"
 except Exception as e:out["error"]=type(e).__name__+": "+str(e)[:260]
 file=Path(a.output);file.parent.mkdir(parents=True,exist_ok=True)
 file.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
