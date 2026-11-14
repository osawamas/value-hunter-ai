/* v187: aggregate source-bound bank issuer research, not an SGX sector index. */
"use strict";
(function(root){
 function validate(feed,bundle){
  if(feed?.schema_version!=="value_hunter_web_v29"||feed.ranking_enabled!==false||
     feed.ranking_eligible_count!==0||
     bundle?.schema_version!=="sgx-big3-normalized-bank-quarters-v186"||
     bundle.period_end!=="2026-09-30"||bundle.unit!=="SGD_millions"||
     bundle.registered_banks!==3||
     bundle.all_three_original_source_hashes_checked!==true||
     bundle.derived_sums_only_not_independent_financial_audit!==true||
     bundle.independent_third_party_financial_verification!==false||
     bundle.authentic_current_sgx_execution_quotes_verified!==false||
     bundle.latest_treasury_adjusted_share_counts_verified!==false||
     bundle.current_market_cap_per_pbr_verified!==false||
     bundle.ranking_eligible!==false||
     !Array.isArray(bundle.entries)||bundle.entries.length!==3)
    throw Error("Unverified bank quarterly source aggregation");
  const expected={D05:{q3profit:2813,nineprofit:8822,q3nii:3711,ninenii:10786},
                  O39:{q3profit:2042,nineprofit:6237,q3nii:2313,ninenii:6798},
                  U11:{q3profit:1250,nineprofit:4165,q3nii:2278,ninenii:6900}};
  for(const symbol of Object.keys(expected)){
    const matches=bundle.entries.filter(e=>e.symbol===symbol);
    if(matches.length!==1||feed.records.filter(e=>e.symbol===symbol&&e.ranking_eligible===false).length!==1)
      throw Error("SGX issuer record not unique");
    const e=matches[0];
    if(e.unit!=="SGD_millions"||e.period_end!=="2026-09-30"||
       !/^[a-f0-9]{64}$/.test(e.sha)||!/^https:\/\/links\.sgx\.com\//.test(e.source))
      throw Error("Bank original digest/source not admissible");
    for(const [key,value] of Object.entries(expected[symbol]))
      if(e[key]!==value)throw Error("Original bank source amount differs "+symbol+"/"+key);
  }
  const sums=Object.fromEntries(["q3profit","nineprofit","q3nii","ninenii"]
   .map(k=>[k,bundle.entries.reduce((v,e)=>v+e[k],0)]));
  if(sums.q3profit!==6105||sums.nineprofit!==19224||
     sums.q3nii!==8302||sums.ninenii!==24484||
     bundle.total_3q26_bank_net_profit!==sums.q3profit||
     bundle.total_9m26_bank_net_profit!==sums.nineprofit||
     bundle.total_3q26_net_interest_income!==sums.q3nii||
     bundle.total_9m26_net_interest_income!==sums.ninenii)
    throw Error("Three bank original SGX totals not arithmetically consistent");
  return sums;
 }
 async function render(){
  const tbody=document.getElementById("big3BankSummaryRows");
  const status=document.getElementById("big3BankSummaryStatus");
  if(!tbody||!status)return;
  try{
   const files=await Promise.all(["./data/latest.json","./data/sgx-big3-bank-research-v186.json"]
     .map(async p=>{const response=await fetch(p,{cache:"no-store"});if(!response.ok)throw Error("HTTP");return response.json()}));
   const x=validate(...files);
   const tr=document.createElement("tr");
   for(const value of [x.q3profit,x.nineprofit,x.q3nii,x.ninenii]){
     const td=document.createElement("td");td.textContent=value.toLocaleString("ja-JP");tr.append(td);
   }
   tbody.replaceChildren(tr);
   status.textContent="単位：百万SGD。DBS・OCBC・UOBの3社だけの2026年3Q/9か月累計を加算。SGX全上場銀行や市場全体の統計ではない。独立数値監査、最新株価・株数の認証は未完。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=4;td.textContent="3社の原本照合が完了していないため合計を表示しない";
   tr.append(td);tbody.replaceChildren(tr);status.textContent="比較データの照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
