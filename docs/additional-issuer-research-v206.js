/* v206: research-only source display for two new issuers, no financial-feed insertion */
"use strict";
(function(root){
 function validate(feed,seed,doc){
  if(feed?.schema_version!=="value_hunter_web_v29"||
   feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
   feed.coverage?.registered_count!==7||
   seed?.schema_version!=="sgx-official-first-batch-board-lot-v196"||
   seed.official_full_security_master_obtained!==false||
   doc?.schema_version!=="sgx-additional-issuer-fy2025-research-v206"||
   doc.original_source_sha256_verified!==false||
   doc.independent_third_party_numeric_verification!==false||
   doc.registered_financial_count_increment!==0||
   doc.ranking_eligible_count_increment!==0||
   doc.licensed_timed_sgx_quotes_available!==false||
   !Array.isArray(doc.items)||doc.items.length!==2)
   throw Error("New issuer research still unverified");
  const expected={BN4:[5983,5784,789,940],V03:[2534.5,2735.9,227,245]};
  return ["BN4","V03"].map(symbol=>{
   const xs=doc.items.filter(x=>x.symbol===symbol);
   if(xs.length!==1||!seed.rows.some(x=>x.symbol===symbol)||
      feed.records.some(x=>x.symbol===symbol))
     throw Error("Research issuer scope changed");
   const r=xs[0],e=expected[symbol];
   if([r.revenue_2025_m_sgd,r.revenue_2024_m_sgd,
       r.reported_parent_net_profit_2025_m_sgd,
       r.reported_parent_net_profit_2024_m_sgd].some((v,i)=>v!==e[i])||
     r.financial_feed_registered!==false||r.ranking_eligible!==false||
     r.latest_shares_and_quote_not_verified!==true||
     r.adjusted_profit_excluded_from_reported_comparison!==true||
     !/^https:\/\//.test(r.source_url))
    throw Error("New issuer reported annual amounts changed");
   if(symbol==="BN4"&&r.adjusted_new_keppel_profit_2025_m_sgd!==1100)
    throw Error("Adjusted Keppel profit confused with reported");
   return {symbol,issuer:r.name,revenue:r.revenue_2025_m_sgd,
    reported_profit:r.reported_parent_net_profit_2025_m_sgd,
    income_basis:r.revenue_basis,source:r.source_url};
  });
 }
 async function render(){
  const status=document.getElementById("additionalIssuerResearchStatus");
  const tbody=document.getElementById("additionalIssuerResearchRows");
  if(!status||!tbody)return;
  try{
   const files=await Promise.all(
    ["./data/latest.json","./data/sgx-official-batch-seed-v196.json",
      "./data/sgx-additional-issuer-fy2025-v206.json"].map(async p=>{
       const res=await fetch(p,{cache:"no-store"});
       if(!res.ok)throw Error("HTTP");return res.json();
      }));
   const rows=validate(...files),frag=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const value of [r.symbol,r.issuer,r.revenue,r.reported_profit,r.income_basis]){
      const td=document.createElement("td");
      td.textContent=typeof value==="number"?value.toLocaleString("ja-JP"):value;
      tr.append(td);
    }
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=r.source;a.textContent="発行体資料";a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="2025年度の発行体資料による予備調査のみ。単位：百万SGD。BN4収益は継続事業、利益は非継続事業を含む報告利益。調整後利益を混ぜない。財務登録・独立検証・株価と株数照合は未完。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="新規発行体の資料照合が未完了のため非表示";
   tr.append(td);tbody.replaceChildren(tr);status.textContent="資料検証待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
