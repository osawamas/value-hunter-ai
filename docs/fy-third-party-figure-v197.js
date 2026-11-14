/* v197: fixed public third-party FY2025 research observation.
   Cross-source rounded figures are not independent assurance or authorized quote data. */
"use strict";
(function(root){
 function validate(feed,data){
  if(feed?.schema_version!=="value_hunter_web_v29"||
    feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
    data?.schema_version!=="sgx-fy2025-third-party-figures-v197"||
    data.period_end!=="2025-12-31"||
    data.third_party_public_web_summary_not_audit!==true||
    data.external_data_methodology_independently_verified!==false||
    data.operating_income_definition_not_comparable!==true||
    data.independent_audit_requirement_satisfied!==false||
    data.official_current_quote_verified!==false||
    data.ranking_eligible_count!==0||
    data.financial_feed_modified!==false||
    !Array.isArray(data.records)||data.records.length!==2)
   throw Error("FY2025 external figure research not admissible");
  const expected={G13:{rev:2452053,profit:390346,operating:506609,extRev:2452,extProfit:390.35,extOp:450.46},
                  S63:{rev:12346426,profit:462770,operating:843116,extRev:12346,extProfit:462.77,extOp:1144}};
  const out=[];
  for(const symbol of ["G13","S63"]){
   const r=data.records.filter(x=>x.symbol===symbol),orig=feed.records?.filter(x=>x.symbol===symbol);
   if(r.length!==1||orig?.length!==1)throw Error("Issuer mismatch");
   const e=r[0],f=orig[0],want=expected[symbol];
   if(f.ranking_eligible!==false||
    f.fiscal_year!==2025||
    f.revenue_sgd_thousands!==want.rev||
    f.attributable_profit_sgd_thousands!==want.profit||
    e.issuer_revenue_thousands!==want.rev||
    e.issuer_parent_profit_thousands!==want.profit||
    e.issuer_reported_operating_profit_thousands!==want.operating||
    e.external_revenue_millions!==want.extRev||
    e.external_net_income_millions!==want.extProfit||
    e.external_operating_income_millions!==want.extOp||
    e.operating_income_comparable!==false||
    e.may_promote_to_ranking!==false||
    !/^https:\/\/stockanalysis\.com\/quote\/sgx\//.test(e.source))
    throw Error("FY2025 matched values changed "+symbol);
   const revDiff=Math.abs(e.external_revenue_millions-want.rev/1000);
   const profitDiff=Math.abs(e.external_net_income_millions-want.profit/1000);
   if(revDiff>0.5||profitDiff>0.0051||
    Math.abs(revDiff-e.revenue_absolute_diff_millions)>1e-9||
    Math.abs(profitDiff-e.parent_profit_absolute_diff_millions)>1e-9)
    throw Error("External provider rounding mismatch");
   out.push({symbol,revenue_m_sgd:want.rev/1000,
    source_reported_revenue_m_sgd:e.external_revenue_millions,
    profit_m_sgd:want.profit/1000,
    source_reported_profit_m_sgd:e.external_net_income_millions,
    external_url:e.source});
  }
  return out;
 }
 async function render(){
  const tbody=document.getElementById("thirdPartyFyCompareRows"),status=document.getElementById("thirdPartyFyCompareStatus");
  if(!tbody||!status)return;
  try{
   const [feed,data]=await Promise.all(["./data/latest.json","./data/sgx-independent-figure-research-v197.json"]
    .map(async url=>{const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json()}));
   const entries=validate(feed,data),frag=document.createDocumentFragment();
   for(const x of entries){
    const tr=document.createElement("tr");
    for(const val of [x.symbol,x.revenue_m_sgd,x.source_reported_revenue_m_sgd,
      x.profit_m_sgd,x.source_reported_profit_m_sgd,"定義が異なるため比較しない"]){
     const td=document.createElement("td");td.textContent=typeof val==="number"?val.toLocaleString("ja-JP"):val;tr.append(td);
    }
    const td=document.createElement("td"),a=document.createElement("a");
    a.textContent="外部資料";a.href=x.external_url;a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="FY2025・百万SGDの参考照合。外部掲載値は丸めあり。営業利益はサイトと発行体で定義が一致しないため比較対象外。外部数値の監査・一次データ独立再計算は未完で、ランキング判定には反映しない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=7;td.textContent="外部照合資料が不整合のため表示しない";tr.append(td);tbody.replaceChildren(tr);
   status.textContent="外部FY2025数値の照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
