/* v288 UOB same-issuer 3Q/9M PDF on two distinct official publishing origins.
 * Exact values match, but no third-party independent financial audit.
 */
"use strict";
(function(root){
 function verify(primary,sgx,finance){
  if(primary?.schema_version!=="uob-3q26-issuer-owned-pdf-original-v288"||
     primary.symbol!=="U11"||primary.period_end!=="2026-09-30"||
     primary.issuer_pdf_size_bytes!==334214||
     primary.issuer_pdf_sha256!=="69d0a461f740beb8eea8605c19e5e0e44f6469a4be630287b87ffb035ea89ff5"||
     primary.issuer_pdf_explicit_table_match!==true||
     primary.issuer_same_organisation_not_independent_audit!==true||
     primary.independent_financial_audit_complete!==false||
     primary.current_share_count_verified!==false||
     primary.current_market_quote_license_verified!==false||
     primary.rank_eligible!==false||
     sgx?.schema_version!=="sgx-big3-normalized-bank-quarters-v186"||
     sgx.period_end!==primary.period_end||
     sgx.ranking_eligible!==false||sgx.unit!=="SGD_millions"||
     finance?.ranking_enabled!==false||finance.ranking_eligible_count!==0)
    throw Error("UOB発行体PDFのSHA・範囲に不整合");
  const row=sgx.entries?.find(x=>x.symbol==="U11");
  const nums=primary.checked_values_sgd_millions;
  if(!row||row.sha!==primary.sgx_pdf_sha256||row.source!==primary.sgx_pdf_url||
     nums?.nine_month_profit!==row.nineprofit||
     nums?.third_quarter_profit!==row.q3profit||
     nums?.nine_month_net_interest_income!==row.ninenii||
     nums?.third_quarter_net_interest_income!==row.q3nii)
    throw Error("UOB原本PDFの9M・3Q利益と純金利収入が不一致");
  return {values:[
   ["3Q26 net profit",row.q3profit],
   ["9M26 net profit",row.nineprofit],
   ["3Q26 net interest income",row.q3nii],
   ["9M26 net interest income",row.ninenii]
  ],officialIssuer:primary.issuer_pdf_url,originalSgx:row.source,
   hash:primary.issuer_pdf_sha256,independentAudited:false,rankingEligible:false};
 }
 async function show(){
  const status=document.getElementById("uobSecondaryIssuerStatus");
  const body=document.getElementById("uobSecondaryIssuerRows");
  if(!status||!body)return;
  try{
   const inputs=await Promise.all([
    "./data/uob-issuer-pdf-q3-2026-v288.json",
    "./data/sgx-big3-bank-research-v186.json",
    "./data/latest.json"
   ].map(async url=>{
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    return response.json();
   }));
   const v=verify(...inputs);
   const fragment=document.createDocumentFragment();
   for(const [name,amount] of v.values){
    const tr=document.createElement("tr");
    for(const label of [name,amount.toLocaleString("ja-JP")+" 百万SGD",
      "SGX掲載の発行体PDFと同じ精密値"]){
     const cell=document.createElement("td");
     cell.textContent=label;tr.append(cell);
    }
    fragment.append(tr);
   }
   body.replaceChildren(fragment);
   status.textContent="UOB公式原本PDFの9M・3Q決算表を直接取得・SHA256照合し、SGX掲載資料の利益と純金利収入4項目に一致。同一発行体の別掲載で、独立監査・株価・ランキング検証ではない。";
   for(const [id,href,sha] of [
    ["uobSecondaryIssuerPdf",v.officialIssuer,v.hash],
    ["uobSecondarySgxPdf",v.originalSgx,null]
   ]){
    const a=document.getElementById(id);
    if(a){a.href=href;a.rel="noopener noreferrer";a.target="_blank";
     if(sha)a.title="公式PDF原本SHA-256："+sha;}
   }
  }catch{
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=3;td.textContent="原本検証失敗のため表示不可";tr.append(td);body.append(tr);
   status.textContent="UOBの追加原本を検証できない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={verify};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",show);
})(typeof window!=="undefined"?window:null);
