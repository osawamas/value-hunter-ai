/* v160: OCBC original dated Q3 bank balance overview; no present market PBR. */
"use strict";
(function(root){
 function validate(feed,bank){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     feed.records?.filter(r=>r.symbol==="O39"&&r.ranking_eligible===false).length!==1||
     bank?.status!=="OCBC_Q3_PRIMARY_BANK_BALANCE_ROWS_PARSED"||
     bank.schema_version!=="sgx-ocbc-q3-balance-probe-v159")
   throw Error("Not an authenticated historical OCBC bank balance source");
  const x=bank.record;
  if(!x||x.schema_version!=="sgx-ocbc-q3-bank-balance-selected-v159"||
     x.symbol!=="O39"||x.period_end_date!=="2026-09-30"||
     x.unit!=="SGD_millions"||
     x.selected_bank_items?.ordinary_equity?.sgd_millions!==60899||
     x.selected_bank_items?.equity_attributable_to_bank_equity_holders?.sgd_millions!==63347||
     x.selected_bank_items?.total_assets?.sgd_millions!==731689||
     x.selected_bank_items?.net_customer_loans?.sgd_millions!==366929||
     x.selected_bank_items?.deposits_nonbank_customers?.sgd_millions!==461462||
     x.attributable_equity_less_ordinary_equity!==2448||
     x.difference_is_not_identified_as_noncontrolling_interest!==true||
     x.bank_ordinary_equity_not_assumed_group_equity!==true||
     x.not_full_audited_bank_statement!==true||
     x.independent_third_party_numbers_verified!==false||
     x.current_treasury_adjusted_shares_verified!==false||
     x.current_sgx_quote_verified!==false||
     x.pbr_eligible!==false||x.ranking_eligible!==false||
     !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/A9CW58STOPTDX0HG\//.test(x.official_source_pdf_url))
   throw Error("OCBC interim bank equity values are unverified or inconsistent");
  return {assets:731689,loans:366929,deposits:461462,
    ordinary:60899,attributable:63347,difference:2448,
    source:x.official_source_pdf_url};
 }
 const fmt=n=>n.toLocaleString("ja-JP");
 async function render(){
  const body=document.getElementById("ocbcBalanceRows"),status=document.getElementById("ocbcBalanceStatus");
  if(!body||!status)return;
  try{
   const files=await Promise.all(["./data/latest.json","./data/sgx-ocbc-bank-balance-v159.json"].map(async path=>{
     const response=await fetch(path,{cache:"no-store"});
     if(!response.ok)throw Error("HTTP "+response.status);
     return response.json();
   }));
   const r=validate(...files),tr=document.createElement("tr");
   for(const value of ["2026年9月末",fmt(r.assets),fmt(r.loans),fmt(r.deposits),fmt(r.ordinary),fmt(r.attributable),fmt(r.difference)]){
     const td=document.createElement("td");td.textContent=value;tr.append(td);
   }
   body.replaceChildren(tr);
   status.textContent="単位：百万SGD。株主帰属持分と普通株主持分は別の概念。差額を非支配株主持分と決めつけず、2026年9月末の発行会社資料として表示。現在PBRには使用しない。";
  }catch(error){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=7;td.textContent="OCBC原本の貸借対照表を照合できないため非表示";
   tr.append(td);body.replaceChildren(tr);status.textContent="銀行の財務原本照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
