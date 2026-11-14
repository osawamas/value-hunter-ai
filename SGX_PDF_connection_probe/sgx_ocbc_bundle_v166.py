"""v166: consolidated OCBC Q3 2026 bank issuer research bundle.

All source documents are original SGX attachment captures from same
issuer. Independence is NOT achieved by having multiple OCBC PDF files.
This is NOT an investable or price-verified SGX bank record.
"""
import argparse, hashlib, json
from pathlib import Path

INPUTS={
 "originals":("sgx-ocbc-q3-pdf-originals-v145","SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED"),
 "rounded":("sgx-ocbc-3q26-official-bank-results-v146","OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED"),
 "ratios":("sgx-ocbc-3q26-bank-ratio-research-v149","OCBC_3Q26_ISSUER_BANK_RATIOS_OBSERVED_IN_PRIMARY_PDF"),
 "exact":("sgx-ocbc-q3-exact-bank-profit-v152","OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED"),
 "income":("sgx-ocbc-bank-income-components-v154","OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED"),
 "allowances":("sgx-ocbc-9m26-allowance-components-v156","OCBC_9M26_ALLOWANCE_BREAKDOWN_RECONCILED_IN_PRIMARY_PDF"),
 "balance":("sgx-ocbc-q3-bank-balance-selected-v159","OCBC_Q3_PRIMARY_BANK_BALANCE_ROWS_PARSED")
}
KEYS={
 "rounded":"original_sgx_pdf_sha256",
 "ratios":"sgx_primary_pdf_sha256",
 "exact":"official_press_sha256",
 "income":"original_pdf_sha256",
 "allowances":"original_sgx_sha256",
 "balance":"official_source_pdf_sha256"
}
def combine(data):
 if not isinstance(data,dict) or set(data)!=set(INPUTS):
  raise ValueError("All seven original issuer research source files required")
 records={}
 for key,(schema,status) in INPUTS.items():
  a=data[key]
  if a.get("status")!=status or not isinstance(a.get("record"),dict) or a["record"].get("schema_version")!=schema:
   raise ValueError("Wrong original evidence status/schema "+key)
  records[key]=a["record"]
 original=records["originals"]
 if original.get("symbol")!="O39" or original.get("original_attachment_count")!=3:
  raise ValueError("Incomplete direct SGX PDF originals")
 files=[r for r in original.get("records",[]) if r.get("filename")=="OCBC_3Q26_Results_Press_Release.pdf"]
 if len(files)!=1:raise ValueError("Original SGX press PDF missing")
 pdf=files[0];sha=pdf["sha256"]
 if len(sha)!=64 or any(r.get(field)!=sha for key,r in records.items() if key!="originals" for field in [KEYS[key]]):
  raise ValueError("All 2026Q3 bank research must share actual original press release SHA")
 if any(r.get("symbol")!="O39" for key,r in records.items() if key!="originals"):
  raise ValueError("Issuer cross-matched incorrectly")
 if any(r.get("ranking_eligible") is not False for key,r in records.items() if key!="originals" and "ranking_eligible" in r):
  raise ValueError("Upstream data promoted into rankings")
 e=records["exact"];i=records["income"];a=records["allowances"];b=records["balance"];q=records["rounded"];ratio=records["ratios"]
 if not (e.get("group_profit_3q26_sgd_millions")==2042 and e.get("group_profit_9m26_sgd_millions")==6237 and
         q.get("group_net_profit_3q26_sgd_billion_reported")=="2.04" and
         q.get("group_net_profit_9m26_sgd_billion_reported")=="6.24"):
  raise ValueError("Rounded and exact bank profits differ")
 quarter=i["bank_statements"]["3Q26"]
 nine=i["bank_statements"]["9M26"]
 if (quarter["net_interest_income"]+quarter["non_interest_income"]!=quarter["combined_interest_and_noninterest_income"] or
     nine["net_interest_income"]+nine["non_interest_income"]!=nine["combined_interest_and_noninterest_income"] or
     quarter["allowances_charged"]!=52 or nine["allowances_charged"]!=424):
  raise ValueError("Incorrect bank income period or unit")
 if (a["impaired_asset_allowances_9m26"]+a["non_impaired_asset_allowances_9m26"]!=a["total_allowances_9m26"] or
     a["total_allowances_9m26"]!=nine["allowances_charged"]):
  raise ValueError("Loss allowance parts do not equal actual original bank statement")
 bal=b["selected_bank_items"]
 if (bal["ordinary_equity"]["sgd_millions"]!=60899 or
     bal["equity_attributable_to_bank_equity_holders"]["sgd_millions"]!=63347 or
     b["attributable_equity_less_ordinary_equity"]!=2448 or
     b.get("difference_is_not_identified_as_noncontrolling_interest") is not True):
  raise ValueError("OCBC ordinary and parent attributable equity improperly conflated")
 if (ratio["net_interest_margin_3q26_pct_issuer_reported"]!="1.66" or
     ratio["nonperforming_loan_ratio_pct_issuer_reported"]!="0.8" or
     ratio["cet1_capital_adequacy_ratio_pct_reported"]!="15.5"):
  raise ValueError("Bank quality ratio values differ")
 for key in ("rounded","ratios","exact","income","allowances","balance"):
  row=records[key]
  if any(row.get(k) is True for k in (
      "independent_third_party_earnings_verification",
      "independent_numerical_verification",
      "independent_third_party_profit_verification",
      "independent_third_party_numerical_verification",
      "independent_third_party_financial_verification",
      "independent_third_party_numbers_verified",
      "current_quote_or_shares_verified",
      "current_treasury_adjusted_shares_verified",
      "current_sgx_quote_verified","pbr_eligible")):
   raise ValueError("Unexpected unsupported independent/market verification in "+key)
 return {
  "schema_version":"sgx-ocbc-bank-research-bundle-v166",
  "symbol":"O39","bank":"Oversea-Chinese Banking Corporation Limited",
  "quarter_end":"2026-09-30",
  "sgx_original_pdf_url":pdf["official_sgx_original_url"],
  "sgx_original_pdf_sha256":sha,
  "sgx_original_attachment_count":3,
  "income_statement_sgd_millions":{
   "3Q26":{"group_net_profit":2042,"group_net_profit_previous_year":1978,
            "net_interest_income":quarter["net_interest_income"],
            "non_interest_income":quarter["non_interest_income"],
            "allowances_charged":quarter["allowances_charged"]},
   "9M26":{"group_net_profit":6237,"group_net_profit_previous_year":5677,
            "net_interest_income":nine["net_interest_income"],
            "non_interest_income":nine["non_interest_income"],
            "allowances_charged":nine["allowances_charged"],
            "allowances_impaired_assets":a["impaired_asset_allowances_9m26"],
            "allowances_non_impaired_assets":a["non_impaired_asset_allowances_9m26"]}
  },
  "bank_quality_3q26_reported_pct":{
   "net_interest_margin":ratio["net_interest_margin_3q26_pct_issuer_reported"],
   "nonperforming_loan_ratio":ratio["nonperforming_loan_ratio_pct_issuer_reported"],
   "cet1_capital_ratio":ratio["cet1_capital_adequacy_ratio_pct_reported"],
   "annualised_return_on_equity":ratio["return_on_equity_3q26_annualised_pct_reported"]},
  "bank_balance_2026_09_30_sgd_millions":{
   "ordinary_equity":60899,
   "equity_attributable_to_bank_equity_holders":63347,
   "total_assets":bal["total_assets"]["sgd_millions"],
   "net_loans_to_customers":bal["net_customer_loans"]["sgd_millions"],
   "deposits_nonbank_customers":bal["deposits_nonbank_customers"]["sgd_millions"]},
  "periods_and_units_explicit":True,
  "multiple_sgx_pdfs_same_issuer_not_independent_financial_verification":True,
  "independent_third_party_financial_reperformance":False,
  "2026_interim_covered_by_fy2025_audit":False,
  "current_treasury_shares_verified":False,
  "authenticated_current_exchange_quote_verified":False,
  "per_pbr_and_ranking_permitted":False
 }

def main():
 p=argparse.ArgumentParser()
 for key in (*INPUTS,"output"):p.add_argument("--"+key,required=True)
 a=p.parse_args()
 source={key:json.loads(Path(getattr(a,key)).read_text()) for key in INPUTS}
 out=combine(source)
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Consolidated OCBC bank research",out["quarter_end"],"ranking",out["per_pbr_and_ranking_permitted"])
if __name__=="__main__":main()
