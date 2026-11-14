/* v178 Big Three Q3 2026 net-interest-income source consistency, SGD millions. */
"use strict";
(function(root) {
 function validate(feed,nii,dbs,ocbc,uob){
  if(feed?.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     nii?.status!=="SGX_THREE_BANK_3Q26_NII_PRIMARY_SUM_RECONCILED"||
     nii.record?.schema_version!=="sgx-big3-nii-source-consistency-v177"||
     nii.record.financial_period_end!=="2026-09-30"||
     nii.record.unit!=="SGD_millions"||
     nii.record.source_date_and_unit_consistent!==true||
     nii.record.dbs_trading_pdf_exact_amount_observed!==true||
     nii.record.dbs_trading_pdf_single_table_row_column_reperformance_completed!==false||
     nii.record.sgx_editorial_update_html_fetched_by_pipeline!==false||
     nii.record.independent_third_party_earnings_audit!==false||
     nii.record.current_sgx_trade_quote_or_treasury_shares_verified!==false||
     nii.record.ranking_eligible!==false)
    throw Error("Quarter bank NII source consistency not proven");
  const r=nii.record,n=r.bank_net_interest_income_3q26;
  if(!n||n.D05!==3711||n.O39!==2313||n.U11!==2278||
    n.D05+n.O39+n.U11!==r.three_bank_3q26_nii_sum_sgd_millions||
    r.three_bank_3q26_nii_sum_sgd_millions!==8302)
    throw Error("Incorrect bank sum");
  if(dbs?.status!=="DBS_3Q26_PRIMARY_SGX_ANNOUNCEMENT_AND_PDF_VERIFIED"||
     dbs.record.official_pdf_sha256!==r.dbs_original_slide_source_sha256||
     ocbc?.schema_version!=="sgx-ocbc-bank-research-bundle-v166"||
     ocbc.sgx_original_pdf_sha256!==r.ocbc_official_pdf_sha256||
     ocbc.income_statement_sgd_millions?.["3Q26"]?.net_interest_income!==2313||
     uob?.status!=="UOB_3Q26_9M26_SGX_PRIMARY_TABLE_COLUMNS_VERIFIED"||
     uob.record.official_pdf_sha256!==r.uob_official_pdf_sha256||
     uob.record.period_specific_table_rows?.["Net interest income"]?.["3q26"]!==2278||
     feed.records.filter(x=>["D05","O39","U11"].includes(x.symbol)&&x.ranking_eligible===false).length!==3)
    throw Error("Bank source SHA or issuer time period differs");
  return {dbs:n.D05,ocbc:n.O39,uob:n.U11,total:8302};
 }
 async function render(){
  const body=document.getElementById("bankNiiRows"),status=document.getElementById("bankNiiStatus");
  if(!body||!status)return;
  try{
   const paths=["./data/latest.json","./data/sgx-big3-nii-v177.json",
    "./data/sgx-dbs-2026q3-original-v170.json",
    "./data/sgx-ocbc-bank-research-v166.json",
    "./data/sgx-uob-exact-bank-table-v175.json"];
   const files=await Promise.all(paths.map(async path=>{
    const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw Error("HTTP "+r.status);return r.json();
   }));
   const x=validate(...files);
   const tr=document.createElement("tr");
   for(const amount of [x.dbs,x.ocbc,x.uob,x.total]){
    const td=document.createElement("td");td.textContent=amount.toLocaleString("ja-JP");tr.append(td);
   }
   body.replaceChildren(tr);
   status.textContent="2026年第3四半期の純金利収入、単位：百万SGD。各社のSGX原本資料から取得した数字を算術合計。独立財務監査の完了ではない。";
  }catch(error){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=4;td.textContent="銀行3社の出典照合待ち";tr.append(td);
   body.replaceChildren(tr);status.textContent="数値と原本ハッシュの一致が未確認";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
