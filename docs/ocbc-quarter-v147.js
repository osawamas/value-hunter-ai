/* v147: OCBC bank 2026Q3 original SGX quarterly summary, research only. */
"use strict";
(function(root){
 function validate(feed,original){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     original?.schema_version!=="sgx-ocbc-q3-metrics-probe-v146"||
     original.status!=="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED")
   throw Error("OCBC official quarterly evidence missing");
  const rows=feed.records?.filter(r=>r.symbol==="O39"),o=original.record;
  if(rows?.length!==1||!o||o.schema_version!=="sgx-ocbc-3q26-official-bank-results-v146"||
     o.symbol!=="O39"||o.period_end_date!=="2026-09-30"||o.financial_type!=="BANK"||
     o.group_net_profit_3q26_sgd_billion_reported!=="2.04"||
     o.group_net_profit_9m26_sgd_billion_reported!=="6.24"||
     o.group_net_profit_3q26_yoy_pct_reported!==3||
     o.group_net_profit_9m26_yoy_pct_reported!==10||
     o.reported_values_are_rounded_in_original_release!==true||
     o.independent_third_party_earnings_verification!==false||
     o.quarter_is_audited_annual_2025!==false||
     o.annualised_per_calculated!==false||
     o.exact_sgx_execution_quote_verified!==false||
     o.current_treasury_adjusted_shares_verified!==false||
     o.ranking_eligible!==false||rows[0].ranking_eligible!==false||
     !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/A9CW58STOPTDX0HG\//.test(o.original_sgx_press_release_url)||
     !/^[a-f0-9]{64}$/.test(o.original_sgx_pdf_sha256))
   throw Error("Bank source status or amount contradiction");
  return {symbol:"O39",profitQuarter:"2.04",profitNineMonths:"6.24",
     yoyQuarter:3,yoyNineMonths:10,source:o.original_sgx_press_release_url};
 }
 async function render(){
  const body=document.getElementById("ocbcQuarterRows");
  const info=document.getElementById("ocbcQuarterStatus");
  if(!body||!info)return;
  try{
   const docs=await Promise.all(["./data/latest.json","./data/sgx-ocbc-2026q3-bank-profit-v146.json"]
    .map(async path=>{const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json()}));
   const v=validate(...docs);
   body.replaceChildren();
   const tr=document.createElement("tr");
   for(const value of ["O39 / OCBC","2026年7〜9月","約20.4億SGD（+3%）","約62.4億SGD（1〜9月累計・+10%）","未検証・ランキング除外"]){
    const td=document.createElement("td");td.textContent=value;tr.append(td);
   }
   const sourceTd=document.createElement("td"),a=document.createElement("a");
   a.href=v.source;a.textContent="SGX公式PDF";a.target="_blank";a.rel="noopener noreferrer";
   sourceTd.append(a);tr.append(sourceTd);body.append(tr);
   info.textContent="OCBC公式の2026年3Q決算資料による概数。独立した第三者検証や最新株価・株式数の認証ではなく、現在のPER/PBRには使用しない。";
  }catch(error){
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="OCBC公式業績の照合待ち";tr.append(td);body.append(tr);
   info.textContent="原本の状態が一致しないため表示しない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
