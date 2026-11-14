/* v141: year-2025 audited issuer accounting arithmetic; NOT independent verification. */
"use strict";
(function(root){
 function validate(feed,arithmetic){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(feed.records)||feed.records.length!==7||
     !arithmetic||arithmetic.schema_version!=="sgx-annual-statement-arithmetic-v140"||
     arithmetic.feed_updated_at_utc!==feed.updated_at_utc||
     arithmetic.checked_issuers!==2||arithmetic.arithmetically_reconciled_count!==2||
     arithmetic.independent_numerical_verification_count!==0||
     arithmetic.eligible_count!==0||arithmetic.financial_feed_modified!==false||
     !Array.isArray(arithmetic.records)||arithmetic.records.length!==2)
    throw Error("最新の財務と会計照合の版が一致しない");
  return ["G13","S63"].map(symbol=>{
   const matches=arithmetic.records.filter(x=>x.symbol===symbol);
   const records=feed.records.filter(x=>x.symbol===symbol);
   if(matches.length!==1||records.length!==1)throw Error("Issuer missing");
   const x=matches[0],r=records[0];
   if(x.statement_year!==2025||x.unit!=="SGD_thousands"||
      ![x.assets,x.liabilities,x.group_equity,x.parent_attributable_equity,x.calculated_noncontrolling_interest].every(Number.isSafeInteger)||
      x.assets!==r.assets_sgd_thousands||
      x.liabilities!==r.liabilities_sgd_thousands||
      x.group_equity!==r.equity_sgd_thousands||
      x.parent_attributable_equity!==r.parent_equity_sgd_thousands||
      x.original_annual_report_sha256!==r.financial_pdf_sha256||
      x.assets-x.liabilities!==x.group_equity||
      x.group_equity-x.parent_attributable_equity!==x.calculated_noncontrolling_interest||
      x.same_issuer_audited_statement_arithmetic_passed!==true||
      x.independent_third_party_reperformance_completed!==false||
      x.independent_parent_equity_source_completed!==false||
      x.market_cap_per_pbr_promoted!==false||
      x.ranking_eligible!==false||r.ranking_eligible!==false)
     throw Error("Unverified accounting arithmetic promotion");
   return {symbol,assets:x.assets,liabilities:x.liabilities,
    groupEquity:x.group_equity,parentEquity:x.parent_attributable_equity,
    minority:x.calculated_noncontrolling_interest};
  });
 }
 const fmt=n=>n.toLocaleString("ja-JP");
 async function render(){
  const body=document.getElementById("annualArithmeticRows");
  const info=document.getElementById("annualArithmeticStatus");
  if(!body||!info)return;
  try{
   const docs=await Promise.all(["./data/latest.json","./data/sgx-annual-arithmetic-v140.json"]
    .map(async url=>{const res=await fetch(url,{cache:"no-store"});if(!res.ok)throw Error("HTTP");return res.json();}));
   const rows=validate(...docs);
   body.replaceChildren();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const value of [r.symbol,fmt(r.assets),fmt(r.liabilities),fmt(r.groupEquity),fmt(r.parentEquity),fmt(r.minority),"計算一致・独立数値検証は未完"]){
     const td=document.createElement("td");td.textContent=value;tr.append(td);
    }
    body.append(tr);
   }
   info.textContent="金額は千SGD。2025年度の同一発行会社資料の数値を再計算。親会社株主持分と連結純資産は異なることがある。現在のPBR・ランキング認証ではない。";
  }catch(error){
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=7;td.textContent="新しい財務データとの照合待ちのため非表示";
   tr.append(td);body.append(tr);
   info.textContent="旧版の会計照合結果は使用しない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
