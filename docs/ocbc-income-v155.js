/* v155: display official OCBC banking income components, separate from industrial revenue. */
"use strict";
(function(root){
 const values={"3Q26":{nii:2313,non:1420,total:3733,before:2211,allow:52},
               "9M26":{nii:6798,non:4933,total:11731,before:7129,allow:424}};
 function validate(feed,components,profits){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(feed.records)||feed.records.filter(x=>x.symbol==="O39"&&x.ranking_eligible===false).length!==1||
     components?.status!=="OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED"||
     components.schema_version!=="sgx-ocbc-bank-components-probe-v154"||
     profits?.status!=="OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED")
   throw Error("OCBC source evidence missing");
  const x=components.record,p=profits.record;
  if(!x||x.schema_version!=="sgx-ocbc-bank-income-components-v154"||
     x.symbol!=="O39"||x.period_end_date!=="2026-09-30"||
     x.original_pdf_sha256!==p.official_press_sha256||
     x.original_pdf_url!==p.official_press_pdf_url||
     x.reported_income_components_arithmetically_added!==true||
     x.same_issuer_primary_unaudited_2026_research!==true||
     x.independent_third_party_numerical_verification!==false||
     x.bank_loan_loss_full_reperformance!==false||
     x.validated_fy2025_audited_per!==false||
     x.current_quote_shares_verified!==false||x.ranking_eligible!==false)
   throw Error("Bank statement risk flags/source mismatch");
  return ["3Q26","9M26"].map(period=>{
    const v=x.bank_statements?.[period],expected=values[period];
    if(!v||v.unit!=="SGD_millions"||
       v.net_interest_income!==expected.nii||
       v.non_interest_income!==expected.non||
       v.combined_interest_and_noninterest_income!==expected.total||
       v.operating_profit_before_allowances!==expected.before||
       v.allowances_charged!==expected.allow||
       v.net_interest_income+v.non_interest_income!==v.combined_interest_and_noninterest_income)
      throw Error("Original banking income component changed without validation");
    return {period,...v};
  });
 }
 const fmt=x=>x.toLocaleString("ja-JP");
 async function render(){
  const body=document.getElementById("ocbcIncomeRows");
  const status=document.getElementById("ocbcIncomeStatus");
  if(!body||!status)return;
  try{
   const files=await Promise.all(["./data/latest.json",
     "./data/sgx-ocbc-income-components-v154.json",
     "./data/sgx-ocbc-exact-profit-v152.json"].map(async x=>{
     const r=await fetch(x,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
   }));
   const rows=validate(...files);
   body.replaceChildren();
   for(const x of rows){
    const tr=document.createElement("tr");
    for(const t of [x.period,fmt(x.net_interest_income),fmt(x.non_interest_income),
       fmt(x.combined_interest_and_noninterest_income),fmt(x.operating_profit_before_allowances),
       fmt(x.allowances_charged),"独立検証未完"]){
      const td=document.createElement("td");td.textContent=t;tr.append(td);
    }
    body.append(tr);
   }
   status.textContent="単位：百万SGD。2026年3Q・9か月期の銀行収益内訳。金利収入＋非金利収入の算術加算であり、営業利益や税引後純利益と同一ではない。";
  }catch(error){
   body.replaceChildren();const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=7;td.textContent="原本との照合未完のため非表示";
   tr.append(td);body.append(tr);status.textContent="OCBC銀行の収益内訳は照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
