/* v195: separate bank FY2025 audited issuer figures from 3Q2026 interim figures.
   These issuer-sourced facts are NOT third-party validation or market valuation. */
"use strict";
(function(root){
 const expected={
  D05:{fyIncome:22900,fyParentProfit:10933,q3Profit:2813,q3Nii:3711},
  O39:{fyIncome:14614,fyParentProfit:7422,q3Profit:2042,q3Nii:2313},
  U11:{fyIncome:13808,fyParentProfit:4682,q3Profit:1250,q3Nii:2278}
 };
 function validate(feed,bundle){
  if(feed?.schema_version!=="value_hunter_web_v29"||
   feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
   !Array.isArray(feed.records)||
   bundle?.schema_version!=="sgx-big3-normalized-bank-quarters-v186"||
   bundle.period_end!=="2026-09-30"||bundle.unit!=="SGD_millions"||
   bundle.independent_third_party_financial_verification!==false||
   bundle.authentic_current_sgx_execution_quotes_verified!==false||
   bundle.latest_treasury_adjusted_share_counts_verified!==false||
   bundle.ranking_eligible!==false)
   throw Error("Bank evidence bridge unavailable");
  const entries=[];
  for(const symbol of ["D05","O39","U11"]){
   const matched=feed.records.filter(r=>r.symbol===symbol);
   const q=bundle.entries?.filter(e=>e.symbol===symbol);
   if(matched.length!==1||q?.length!==1)throw Error("Bank issuer duplicate/missing");
   const r=matched[0],v=q[0],fin=r.bank_financial_state;
   if(r.ranking_eligible!==false||fin?.banking_metrics_parsed!==true||
    fin.generic_industrial_metrics_not_applicable!==true||
    fin.fiscal_year!==2025||fin.third_party_numerical_verification!==false||
    fin.current_quote_verified!==false||fin.current_share_count_verified!==false||
    fin.ranking_eligible!==false||
    !/^https:\/\//.test(fin.source_url)||
    !/^[a-f0-9]{64}$/.test(fin.pdf_sha256)||
    !/^[a-f0-9]{64}$/.test(v.sha)||
    v.period_end!=="2026-09-30"||v.unit!=="SGD_millions"||
    r.banking_interim_2026?.pdf_sha256!==v.sha||
    r.banking_interim_2026.period_end!=="2026-09-30"||
    r.banking_interim_2026.not_independently_verified!==true)
    throw Error("Missing source-bound FY/quarter bank evidence "+symbol);
   let annual;
   if(symbol==="D05"){
    const a=r.banking_evidence;
    if(a?.pdf_sha256!==fin.pdf_sha256||a.fiscal_year!==2025)throw Error("DBS annual source");
    annual={income:a.income?.["2025"]?.total_income,profit:a.income?.["2025"]?.profit_attributable_to_parent};
   }else{
    const a=r.banking_audited;
    if(a?.pdf_sha256!==fin.pdf_sha256||a.period_end!=="2025-12-31")
     throw Error("Bank audited source "+symbol);
    annual={income:a.income?.total_income?.["2025"],profit:a.income?.parent_profit?.["2025"]};
   }
   const e=expected[symbol];
   if(annual.income!==e.fyIncome||annual.profit!==e.fyParentProfit||
    v.q3profit!==e.q3Profit||v.q3nii!==e.q3Nii)
    throw Error("Issuer-period amount differs "+symbol);
   entries.push({symbol,fy2025_total_income_m_sgd:annual.income,
    fy2025_parent_profit_m_sgd:annual.profit,q3_2026_profit_m_sgd:v.q3profit,
    q3_2026_net_interest_income_m_sgd:v.q3nii,
    fy_source_url:fin.source_url,fy_pdf_sha256:fin.pdf_sha256,
    q3_source_url:v.source,q3_pdf_sha256:v.sha});
  }
  return entries;
 }
 async function render(){
  const body=document.getElementById("bankFyBridgeRows"),status=document.getElementById("bankFyBridgeStatus");
  if(!body||!status)return;
  try{
   const [feed,bundle]=await Promise.all(
    ["./data/latest.json","./data/sgx-big3-bank-research-v186.json"].map(async url=>{
     const response=await fetch(url,{cache:"no-store"});
     if(!response.ok)throw Error("HTTP");
     return response.json();
    }));
   const entries=validate(feed,bundle);
   const frag=document.createDocumentFragment();
   for(const r of entries){
    const tr=document.createElement("tr");
    for(const val of [r.symbol,r.fy2025_total_income_m_sgd,
      r.fy2025_parent_profit_m_sgd,r.q3_2026_profit_m_sgd]){
     const td=document.createElement("td");
     td.textContent=typeof val==="number"?val.toLocaleString("ja-JP"):val;
     tr.append(td);
    }
    const td=document.createElement("td");
    for(const [title,url] of [["FY2025",r.fy_source_url],["3Q2026",r.q3_source_url]]){
     const a=document.createElement("a");a.href=url;a.target="_blank";
     a.rel="noopener noreferrer";a.textContent=title;td.append(a);
     td.append(document.createTextNode(" "));
    }
    tr.append(td);frag.append(tr);
   }
   body.replaceChildren(frag);
   status.textContent="FY2025は銀行グループの年間総収益・親会社帰属利益、3Q2026は四半期純利益。期間の異なる数字は増減率として比較しない。発行体原本のみで第三者独立照合は未完、投資順位には使わない。単位：百万SGD。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="銀行の年度・四半期資料の整合が取れないため表示しない";
   tr.append(td);body.replaceChildren(tr);status.textContent="原本の照合未完了";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
