/* v207: heterogeneous official-issuer FY2025 metrics are DISPLAYED, never ranked. */
"use strict";
(function(root){
 const permitted={
  G07:{currency:"SGD",metric:"PROFIT_ATTRIBUTABLE_TO_SHAREHOLDERS",amount:1207.1},
  H02:{currency:"SGD",metric:"GROUP_REVENUE",amount:229.967},
  C07:{currency:"USD",metric:"UNDERLYING_NET_PROFIT",amount:1110},
  J36:{currency:"USD",metric:"REPORTED_NET_PROFIT_OR_LOSS",amount:1109},
  K6S:{currency:"USD",metric:"FY2025_IFRS_PROFIT_AFTER_TAX",amount:4119}
 };
 function validate(feed,seed,newResearch,existingResearch){
  if(feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||
   feed.coverage?.registered_count!==7||
   seed?.official_full_security_master_obtained!==false||
   newResearch?.schema_version!=="sgx-remaining-official-seed-fy2025-research-v207"||
   newResearch.independent_third_party_numeric_verification===true||
   newResearch.all_sources_externally_audited_independently!==false||
   newResearch.financial_feed_registered_increment!==0||
   newResearch.ranking_eligible_increment!==0||
   newResearch.cross_currency_peer_ranking_allowed!==false||
   existingResearch?.schema_version!=="sgx-additional-issuer-fy2025-research-v206"||
   !Array.isArray(newResearch.items)||newResearch.items.length!==5||
   existingResearch.items?.length!==2)
   throw Error("New issuer research source not compatible");
  const ids=[...existingResearch.items,...newResearch.items].map(x=>x.symbol);
  if(new Set(ids).size!==7||
     seed.rows.filter(x=>ids.includes(x.symbol)).length!==7)
   throw Error("Official seed research coverage mismatch");
  const rows=[];
  for(const symbol of ["G07","H02","C07","J36","K6S"]){
   const matching=newResearch.items.filter(x=>x.symbol===symbol),p=permitted[symbol];
   if(matching.length!==1||feed.records.some(x=>x.symbol===symbol))throw Error("Issuer missing or duplicate");
   const x=matching[0],m=x.metrics?.find(y=>y.name===p.metric);
   if(!m||m.y2025!==p.amount||m.unit!==p.currency+"_millions"||
      x.reporting_currency!==p.currency||
      x.financial_feed_registered!==false||x.ranking_eligible!==false||
      x.independently_verified!==false||
      !/^https:\/\//.test(x.source_url))
    throw Error("Noncomparable issuer metric changed");
   rows.push({symbol,issuer:x.issuer,metric:m.name,amount:m.y2025,
    currency:x.reporting_currency,source:x.source_url});
  }
  return rows;
 }
 async function render(){
  const tbody=document.getElementById("remainingIssuerResearchRows");
  const status=document.getElementById("remainingIssuerResearchStatus");
  if(!tbody||!status)return;
  try{
   const [feed,seed,first,rest]=await Promise.all(
    ["./data/latest.json","./data/sgx-official-batch-seed-v196.json",
    "./data/sgx-additional-issuer-fy2025-v206.json",
    "./data/sgx-remaining-issuer-research-v207.json"].map(async p=>{
     const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
    }));
   const rows=validate(feed,seed,rest,first),frag=document.createDocumentFragment();
   for(const x of rows){
    const tr=document.createElement("tr");
    for(const v of [x.symbol,x.issuer,x.metric,x.amount.toLocaleString("ja-JP"),x.currency]){
     const td=document.createElement("td");td.textContent=v;tr.append(td);
    }
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=x.source;a.textContent="発行体資料";a.rel="noopener noreferrer";a.target="_blank";
    td.append(a);tr.append(td);frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="SGX公式限定11証券のうち財務未登録7証券の調査資料を収集（v206の2社＋v207の5社）。指標・通貨が異なるため金額を横比較せず、独立監査・最新株価・株式数・ランキングへの採用は未完。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="発行体の資料照合が未完了のため非表示";
   tr.append(td);tbody.replaceChildren(tr);status.textContent="根拠データ確認待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
