/* v167: compact official OCBC bank evidence headline powered by v166 bundle. */
"use strict";
(function(root){
 function validate(feed,bundle){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     feed.records?.filter(x=>x.symbol==="O39"&&x.ranking_eligible===false).length!==1||
     !bundle||bundle.schema_version!=="sgx-ocbc-bank-research-bundle-v166"||
     bundle.symbol!=="O39"||bundle.quarter_end!=="2026-09-30"||
     !/^[a-f0-9]{64}$/.test(bundle.sgx_original_pdf_sha256)||
     bundle.sgx_original_attachment_count!==3||
     bundle.multiple_sgx_pdfs_same_issuer_not_independent_financial_verification!==true||
     bundle.independent_third_party_financial_reperformance!==false||
     bundle["2026_interim_covered_by_fy2025_audit"]!==false||
     bundle.current_treasury_shares_verified!==false||
     bundle.authenticated_current_exchange_quote_verified!==false||
     bundle.per_pbr_and_ranking_permitted!==false)
   throw Error("Latest banking bundle is not safe as an issuer research summary");
  const q=bundle.income_statement_sgd_millions?.["3Q26"],
   nine=bundle.income_statement_sgd_millions?.["9M26"],
   ratios=bundle.bank_quality_3q26_reported_pct,
   balance=bundle.bank_balance_2026_09_30_sgd_millions;
  if(q?.group_net_profit!==2042||nine?.group_net_profit!==6237||
     q.net_interest_income!==2313||q.non_interest_income!==1420||
     nine.allowances_impaired_assets+nine.allowances_non_impaired_assets!==nine.allowances_charged||
     nine.allowances_charged!==424||
     ratios?.cet1_capital_ratio!=="15.5"||
     ratios.nonperforming_loan_ratio!=="0.8"||
     balance?.ordinary_equity!==60899||
     balance.equity_attributable_to_bank_equity_holders!==63347||
     !/^https:\/\/links\.sgx\.com\//.test(bundle.sgx_original_pdf_url))
   throw Error("Unsupported OCBC original-source headline");
  return {profit:q.group_net_profit,cet1:ratios.cet1_capital_ratio,
    npl:ratios.nonperforming_loan_ratio,ordinaryEquity:balance.ordinary_equity,
    quarter:"2026年第3四半期"};
 }
 async function render(){
  const e=document.getElementById("ocbcBundleHeadline");
  if(!e)return;
  try{
   const [feed,bundle]=await Promise.all(["./data/latest.json",
    "./data/sgx-ocbc-bank-research-v166.json"].map(async path=>{
      const res=await fetch(path,{cache:"no-store"});if(!res.ok)throw Error("HTTP");return res.json();
   }));
   const d=validate(feed,bundle);
   e.textContent="3Q純利益 "+d.profit.toLocaleString("ja-JP")+"百万SGD / CET1 "+d.cet1+
      "% / 不良債権比率 "+d.npl+"% · 6表を展開（2026年発行会社資料・独立検証未完）";
  }catch(error){
   e.textContent="SGX原本の確認結果を照合中。最新検証が揃うまで数値を表示しない";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
