"""v156: OCBC nine-month loan and other-asset allowance composition.

Source is the original SGX-hosted OCBC 2026 Q3 press PDF. All values are
SGD millions from same-issuer quarterly release, not independently audited.
"""
import argparse,hashlib,json,re
from pathlib import Path
from sgx_ocbc_q3_pdfs_v145 import fetch_pdf
NAME="OCBC_3Q26_Results_Press_Release.pdf"

def extract(raw,manifest,components):
 if (manifest.get("status")!="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED" or
     components.get("status")!="OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED"):
  raise ValueError("Unverified source chain")
 candidates=[x for x in manifest.get("record",{}).get("records",[]) if x.get("filename")==NAME]
 if len(candidates)!=1:raise ValueError("OCBC original announcement PDF missing")
 p=candidates[0]
 if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or hashlib.sha256(raw).hexdigest()!=p["sha256"]:
  raise ValueError("Original SHA mismatch")
 bank=components.get("record",{})
 if (bank.get("original_pdf_sha256")!=p["sha256"] or
     bank.get("bank_statements",{}).get("9M26",{}).get("allowances_charged")!=424 or
     bank.get("ranking_eligible") is not False):
  raise ValueError("Wrong bank income component proof")
 import fitz
 d=fitz.open(stream=raw,filetype="pdf")
 try:
  text=" ".join(d[4].get_text("text").split())
 finally:d.close()
 expected={
  "impaired_assets":"Allowances for impaired assets of S$190 million",
  "non_impaired_assets":"Allowances for non-impaired assets of S$234 million",
  "total":"For 9M26, total allowances declined 9% to S$424 million"
 }
 for key,phrase in expected.items():
  if text.count(phrase)!=1:raise ValueError("Missing or repeated original allowances evidence "+key)
 if "9M26" not in text or "9M25" not in text:
  raise ValueError("Expected original 9M period not found")
 impaired=190;nonimpaired=234;total=424
 if impaired+nonimpaired!=total:raise ValueError("Bank allowances arithmetic failed")
 return {
  "schema_version":"sgx-ocbc-9m26-allowance-components-v156",
  "symbol":"O39","period_end_date":"2026-09-30","unit":"SGD_millions",
  "original_sgx_pdf_url":p["official_sgx_original_url"],
  "original_sgx_sha256":p["sha256"],
  "source_pdf_page":5,
  "impaired_asset_allowances_9m26":impaired,
  "non_impaired_asset_allowances_9m26":nonimpaired,
  "total_allowances_9m26":total,
  "computed_composition_difference":impaired+nonimpaired-total,
  "exact_text_original_same_issuer_confirmed":True,
  "full_expected_credit_loss_validation":False,
  "independent_third_party_financial_verification":False,
  "current_quote_or_shares_verified":False,
  "ranking_eligible":False}

def main():
 p=argparse.ArgumentParser()
 for k in ("originals","components","output"):p.add_argument("--"+k,required=True)
 args=p.parse_args()
 m=json.loads(Path(args.originals).read_text())
 c=json.loads(Path(args.components).read_text())
 out={"schema_version":"sgx-ocbc-allowances-probe-v156","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  item=next(x for x in m["record"]["records"] if x["filename"]==NAME)
  out["record"]=extract(fetch_pdf(item["official_sgx_original_url"]),m,c)
  out["status"]="OCBC_9M26_ALLOWANCE_BREAKDOWN_RECONCILED_IN_PRIMARY_PDF"
 except Exception as exc:out["error"]=type(exc).__name__+": "+str(exc)[:270]
 target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
