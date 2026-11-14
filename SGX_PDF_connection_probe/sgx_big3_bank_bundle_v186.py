"""v186 normalize three banks Q3 and 9M 2026 from SGX original evidence.

Issuer-original reporting, not cross-issuer independent accounting work.
No current SGX quote/treasury-share certification, no investment ranking.
"""
import argparse,json,re
from pathlib import Path

def normalize(dbs,ocbc,uob,nii):
 if (dbs.get("status")!="DBS_3Q26_9M26_PRIMARY_SGX_TABLE_COLUMNS_RECONCILED" or
     ocbc.get("schema_version")!="sgx-ocbc-bank-research-bundle-v166" or
     uob.get("status")!="UOB_3Q26_9M26_SGX_PRIMARY_TABLE_COLUMNS_VERIFIED" or
     nii.get("status")!="SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED"):
  raise ValueError("Three primary financial source chains incomplete")
 d=dbs["record"];o=ocbc;u=uob["record"];n=nii["record"]
 if (d.get("symbol")!="D05" or o.get("symbol")!="O39" or u.get("symbol")!="U11" or
     any(x!="2026-09-30" for x in (d["financial_period_end"],o["quarter_end"],u["financial_period_end"],n["financial_period_end"]))):
  raise ValueError("Mismatch fiscal periods")
 if (d["independent_numerical_verification"] is not False or
     o["independent_third_party_financial_reperformance"] is not False or
     u["independent_third_party_numerical_reperformance"] is not False or
     n["independent_third_party_earnings_audit"] is not False or
     d["ranking_eligible"] is not False or u["ranking_eligible"] is not False or
     o["per_pbr_and_ranking_permitted"] is not False):
  raise ValueError("Source is not permitted as independently verified")
 for original,mirror in (
    (d["original_pdf_sha256"],n["dbs_official_trading_pdf_sha256"]),
    (o["sgx_original_pdf_sha256"],n["ocbc_official_pdf_sha256"]),
    (u["official_pdf_sha256"],n["uob_official_pdf_sha256"])):
  if not re.fullmatch("[0-9a-f]{64}",original) or original!=mirror:
   raise ValueError("Cross-source SGX document digest mismatch")
 def check(result,truth):
  if result!=truth:raise ValueError("SGX issuer quarterly financial amounts unexpectedly changed")
  return result
 raw=[
  {"symbol":"D05","issuer":"DBS","sha":d["original_pdf_sha256"],
   "source":d["original_sgx_pdf_url"],
   "q3profit":check(d["net_profit_3q26_sgd_millions"],2813),
   "q3prior":check(int(d["exact_original_table_rows"]["Net profit"]["source_column_values"][1].replace(",","")),2954),
   "nineprofit":check(d["net_profit_9m26_sgd_millions"],8822),
   "nineprior":check(int(d["exact_original_table_rows"]["Net profit"]["source_column_values"][6].replace(",","")),8675),
   "q3nii":check(d["net_interest_income_3q26_sgd_millions"],3711),
   "ninenii":check(int(d["exact_original_table_rows"]["Of which: Net interest income"]["source_column_values"][5].replace(",","")),10786)},
  {"symbol":"O39","issuer":"OCBC","sha":o["sgx_original_pdf_sha256"],
   "source":o["sgx_original_pdf_url"],
   "q3profit":check(o["income_statement_sgd_millions"]["3Q26"]["group_net_profit"],2042),
   "q3prior":check(o["income_statement_sgd_millions"]["3Q26"]["group_net_profit_previous_year"],1978),
   "nineprofit":check(o["income_statement_sgd_millions"]["9M26"]["group_net_profit"],6237),
   "nineprior":check(o["income_statement_sgd_millions"]["9M26"]["group_net_profit_previous_year"],5677),
   "q3nii":check(o["income_statement_sgd_millions"]["3Q26"]["net_interest_income"],2313),
   "ninenii":check(o["income_statement_sgd_millions"]["9M26"]["net_interest_income"],6798)},
  {"symbol":"U11","issuer":"UOB","sha":u["official_pdf_sha256"],
   "source":u["official_pdf_url"],
   "q3profit":check(u["period_specific_table_rows"]["Net profit"]["3q26"],1250),
   "q3prior":check(u["period_specific_table_rows"]["Net profit"]["3q25"],443),
   "nineprofit":check(u["period_specific_table_rows"]["Net profit"]["9m26"],4165),
   "nineprior":check(u["period_specific_table_rows"]["Net profit"]["9m25"],3271),
   "q3nii":check(u["period_specific_table_rows"]["Net interest income"]["3q26"],2278),
   "ninenii":check(u["period_specific_table_rows"]["Net interest income"]["9m26"],6900)}
 ]
 if sum(x["q3nii"] for x in raw)!=n["three_bank_3q26_nii_sum_sgd_millions"] or n["three_bank_3q26_nii_sum_sgd_millions"]!=8302:
  raise ValueError("Bank NII historical original reconciliation failed")
 for row in raw:
  if row["q3profit"]<=0 or row["q3prior"]<=0 or row["nineprofit"]<row["q3profit"]:
   raise ValueError("Incorrect quarterly bank earnings sign/period")
  if row["q3nii"]<=0 or row["ninenii"]<row["q3nii"]:
   raise ValueError("Incorrect interest income basis")
  row["profit_3q_yoy_pct_recomputed"]=round(100*(row["q3profit"]/row["q3prior"]-1),4)
  row["profit_9m_yoy_pct_recomputed"]=round(100*(row["nineprofit"]/row["nineprior"]-1),4)
  row["period_end"]="2026-09-30"
  row["unit"]="SGD_millions"
 return {"schema_version":"sgx-big3-normalized-bank-quarters-v186",
  "period_end":"2026-09-30","unit":"SGD_millions",
  "registered_banks":3,"entries":raw,
  "total_3q26_net_interest_income":sum(x["q3nii"] for x in raw),
  "total_9m26_net_interest_income":sum(x["ninenii"] for x in raw),
  "total_3q26_bank_net_profit":sum(x["q3profit"] for x in raw),
  "total_9m26_bank_net_profit":sum(x["nineprofit"] for x in raw),
  "all_three_original_source_hashes_checked":True,
  "derived_sums_only_not_independent_financial_audit":True,
  "independent_third_party_financial_verification":False,
  "authentic_current_sgx_execution_quotes_verified":False,
  "latest_treasury_adjusted_share_counts_verified":False,
  "current_market_cap_per_pbr_verified":False,
  "ranking_eligible":False}

def main():
 p=argparse.ArgumentParser()
 for x in ("dbs","ocbc","uob","nii","output"):p.add_argument("--"+x,required=True)
 a=p.parse_args()
 x=[json.loads(Path(getattr(a,k)).read_text()) for k in ("dbs","ocbc","uob","nii")]
 result=normalize(*x)
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("v186",result["total_3q26_bank_net_profit"],result["total_3q26_net_interest_income"],result["ranking_eligible"])
if __name__=="__main__":main()
