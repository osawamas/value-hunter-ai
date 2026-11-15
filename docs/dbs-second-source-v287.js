/* v287 DBS independently fetched bank-owned news HTML is same-issuer corroboration only.
 * Never treat issuer channels as a third-party audit or current price evidence.
 */
"use strict";
(function(root){
 function verify(dbs,sgx,feed){
  if(dbs?.schema_version!=="dbs-3q26-issuer-newsroom-proof-v287"||
     dbs.symbol!=="D05"||dbs.period_end!=="2026-09-30"||
     dbs.issuer_html_bytes!==153882||
     dbs.issuer_html_sha256!=="3f287a5dc29a61a44fcc1c8f635bd085544bd9dd69d8ad59f23ea170c1369e7d"||
     dbs.source_text_identity_date_profit_checks_passed!==true||
     dbs.independent_financial_audit_complete!==false||
     dbs.current_market_quote_licensed!==false||
     dbs.current_ex_treasury_shares_verified!==false||
     dbs.rank_eligible!==false||
     sgx?.schema_version!=="sgx-big3-normalized-bank-quarters-v186"||
     sgx.period_end!==dbs.period_end||sgx.unit!=="SGD_millions"||
     sgx.ranking_eligible!==false||
     feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)
   throw Error("DBS原本・非ランキング条件に不整合");
  const row=sgx.entries?.find(x=>x.symbol==="D05");
  if(!row||row.sha!==dbs.original_sgx_issuer_pdf_sha256||
     row.source!==dbs.original_sgx_issuer_pdf_url||
     row.q3profit!==dbs.profit_3q_sgx_millions||
     row.nineprofit!==dbs.profit_9m_sgx_millions||
     Math.abs(row.q3profit-dbs.issuer_website_q3_rounded_billions*1000)>5||
     Math.abs(row.nineprofit-dbs.issuer_website_nine_month_rounded_billions*1000)>5)
    throw Error("DBS二つの発行体公開経路の数値不一致");
  return {q3:row.q3profit,nine:row.nineprofit,
    rounded3q:dbs.issuer_website_q3_rounded_billions,
    rounded9m:dbs.issuer_website_nine_month_rounded_billions,
    source:dbs.issuer_page_url,sgx:row.source,sha:dbs.issuer_html_sha256,
    independentAudit:false,rankingEligible:false};
 }
 async function mount(){
  const status=document.getElementById("dbsSecondarySourceStatus");
  const body=document.getElementById("dbsSecondarySourceRows");
  if(!status||!body)return;
  try{
   const data=await Promise.all([
    "./data/dbs-issuer-newsroom-3q26-v287.json",
    "./data/sgx-big3-bank-research-v186.json","./data/latest.json"].map(async url=>{
     const resp=await fetch(url,{cache:"no-store"});
     if(!resp.ok)throw Error("HTTP "+resp.status);
     return resp.json();
    }));
   const v=verify(...data);
   body.replaceChildren();
   for(const [name,exact,rounded] of [["3Q26 net profit",v.q3,v.rounded3q],
                                      ["9M26 net profit",v.nine,v.rounded9m]]){
    const tr=document.createElement("tr");
    for(const val of [name,exact.toLocaleString("ja-JP")+" 百万SGD",
                      rounded.toFixed(2)+" billion SGD","同一発行体の丸め値一致"]){
     const td=document.createElement("td");td.textContent=val;tr.append(td);
    }
    body.append(tr);
   }
   status.textContent="DBS発行体サイトの原本HTML SHA-256とSGX掲載決算の利益概数を照合済み。第三者独立監査ではない。";
   const links=[["dbsSecondaryIssuerLink",v.source,v.sha],["dbsSecondarySgxLink",v.sgx,null]];
   for(const [id,url,sha] of links){
    const a=document.getElementById(id);
    if(a){a.href=url;a.target="_blank";a.rel="noopener noreferrer";if(sha)a.title="原本HTML SHA-256："+sha;}
   }
  }catch{
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=4;td.textContent="原本照合不可のため非表示";tr.append(td);body.append(tr);
   status.textContent="DBS 3Q26の2経路照合を検証できない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={verify};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",mount);
})(typeof window!=="undefined"?window:null);
