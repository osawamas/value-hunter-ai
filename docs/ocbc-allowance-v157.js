/* v157: same-issuer SGX OCBC 9M26 allowance composition, not audit or ranking */
"use strict";
(function(root){
 function validate(feed,breakdown,components){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     feed.records?.filter(r=>r.symbol==="O39"&&r.ranking_eligible===false).length!==1||
     breakdown?.status!=="OCBC_9M26_ALLOWANCE_BREAKDOWN_RECONCILED_IN_PRIMARY_PDF"||
     breakdown.schema_version!=="sgx-ocbc-allowances-probe-v156"||
     components?.status!=="OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED")
   throw Error("Official source not validated");
  const b=breakdown.record,c=components.record;
  if(!b||b.schema_version!=="sgx-ocbc-9m26-allowance-components-v156"||
     b.symbol!=="O39"||b.period_end_date!=="2026-09-30"||
     b.unit!=="SGD_millions"||
     b.impaired_asset_allowances_9m26!==190||
     b.non_impaired_asset_allowances_9m26!==234||
     b.total_allowances_9m26!==424||
     b.computed_composition_difference!==0||
     b.impaired_asset_allowances_9m26+b.non_impaired_asset_allowances_9m26!==b.total_allowances_9m26||
     b.original_sgx_sha256!==c.original_pdf_sha256||
     b.original_sgx_pdf_url!==c.original_pdf_url||
     c.bank_statements?.["9M26"]?.allowances_charged!==424||
     b.exact_text_original_same_issuer_confirmed!==true||
     b.full_expected_credit_loss_validation!==false||
     b.independent_third_party_financial_verification!==false||
     b.current_quote_or_shares_verified!==false||b.ranking_eligible!==false)
   throw Error("OCBC allowance composition or provenance mismatch");
  return {impaired:190,nonimpaired:234,total:424,source:b.original_sgx_pdf_url};
 }
 async function render(){
  const body=document.getElementById("ocbcAllowanceRows"),status=document.getElementById("ocbcAllowanceStatus");
  if(!body||!status)return;
  try{
   const [f,b,c]=await Promise.all([
    "./data/latest.json","./data/sgx-ocbc-allowances-v156.json",
    "./data/sgx-ocbc-income-components-v154.json"].map(async x=>{
    const res=await fetch(x,{cache:"no-store"});if(!res.ok)throw Error("HTTP");return res.json();
   }));
   const x=validate(f,b,c);
   const tr=document.createElement("tr");
   for(const str of ["2026年1〜9月",String(x.impaired),String(x.nonimpaired),String(x.total),
       "内訳の算術一致・独立検証は未完"]){
    const td=document.createElement("td");td.textContent=str;tr.append(td);
   }
   body.replaceChildren(tr);
   status.textContent="単位：百万SGD。原本PDFの不良資産・非不良資産向け引当金を照合。信用損失の妥当性を独立監査したものではない。";
  }catch(err){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="原本内訳の照合待ち";tr.append(td);body.replaceChildren(tr);
   status.textContent="不一致のデータは非表示";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
