/* v153: exact SGD-million OCBC 3Q and 9M historical group profit comparison. */
"use strict";
(function(root){
 function validate(feed,exact,rounded){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(feed.records)||feed.records.filter(r=>r.symbol==="O39").length!==1||
     exact?.status!=="OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED"||
     exact.schema_version!=="sgx-ocbc-precise-bank-profit-probe-v152"||
     rounded?.status!=="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED"||
     rounded.schema_version!=="sgx-ocbc-q3-metrics-probe-v146")
   throw Error("Original bank data missing or unsafe");
  const e=exact.record,p=rounded.record;
  if(!e||e.schema_version!=="sgx-ocbc-q3-exact-bank-profit-v152"||
     e.symbol!=="O39"||e.period_end_date!=="2026-09-30"||
     e.official_press_sha256!==p.original_sgx_pdf_sha256||
     e.official_press_pdf_url!==p.original_sgx_press_release_url||
     e.group_profit_3q26_sgd_millions!==2042||
     e.group_profit_9m26_sgd_millions!==6237||
     !Array.isArray(e.exact_statement_profit_rows)||e.exact_statement_profit_rows.length!==2||
     e.exact_statement_profit_rows[0].comparison_sgd_millions!==1978||
     e.exact_statement_profit_rows[1].comparison_sgd_millions!==5677||
     e.exact_statement_profit_rows[0].pdf_page!==2||
     e.exact_statement_profit_rows[1].pdf_page!==4||
     e.same_issuer_rounded_summary_arithmetic_reconciled!==true||
     e.independent_third_party_profit_verification!==false||
     e.fy2025_audit_opinion_applies_to_2026_q3!==false||
     e.current_quote_or_shares_verified!==false||
     e.annual_per_or_pbr_promoted!==false||e.ranking_eligible!==false||
     feed.records.filter(r=>r.symbol==="O39")[0].ranking_eligible!==false)
   throw Error("Banking figure/source mismatch");
  const items=e.exact_statement_profit_rows;
  return items.map((item,i)=>({
   period:i===0?"2026年第3四半期":"2026年1〜9月",
   current:item.current_sgd_millions,previous:item.comparison_sgd_millions,
   yoy:(item.current_sgd_millions/item.comparison_sgd_millions-1)*100,
   source:e.official_press_pdf_url
  }));
 }
 const fmt=n=>n.toLocaleString("ja-JP");
 async function render(){
  const body=document.getElementById("ocbcExactProfitRows");
  const info=document.getElementById("ocbcExactProfitStatus");
  if(!body||!info)return;
  try{
   const files=await Promise.all(["./data/latest.json","./data/sgx-ocbc-exact-profit-v152.json",
    "./data/sgx-ocbc-2026q3-bank-profit-v146.json"].map(async path=>{
      const r=await fetch(path,{cache:"no-store"});
      if(!r.ok)throw Error("HTTP "+r.status);
      return r.json();
   }));
   const rows=validate(...files);
   body.replaceChildren();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const str of [r.period,fmt(r.current),fmt(r.previous),"+"+r.yoy.toFixed(2)+"%","同一発行会社の原本・独立検証は未完"]){
      const td=document.createElement("td");td.textContent=str;tr.append(td);
    }
    body.append(tr);
   }
   info.textContent="単位：百万SGD。SGX公式OCBC資料の表から抽出した数値で前年同期比を再計算。独立した第三者監査・株価認証ではない。";
  }catch(error){
   body.replaceChildren();const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="公式の精密数値を確認できないため非表示";
   tr.append(td);body.append(tr);info.textContent="OCBCの精密値は照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
