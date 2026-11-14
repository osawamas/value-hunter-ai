/* v150: bank-specific OCBC primary 3Q26 ratios, not securities valuation. */
"use strict";
(function(root){
 function validate(feed,quarter,ratios){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     quarter?.status!=="OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED"||
     quarter.schema_version!=="sgx-ocbc-q3-metrics-probe-v146"||
     ratios?.status!=="OCBC_3Q26_ISSUER_BANK_RATIOS_OBSERVED_IN_PRIMARY_PDF"||
     ratios.schema_version!=="sgx-ocbc-bank-ratio-probe-v149")
   throw Error("Bank evidence state missing");
  const x=ratios.record,q=quarter.record;
  if(!x||!q||x.schema_version!=="sgx-ocbc-3q26-bank-ratio-research-v149"||
     x.symbol!=="O39"||x.financial_period_end!=="2026-09-30"||
     x.sgx_primary_pdf_sha256!==q.original_sgx_pdf_sha256||
     x.sgx_primary_pdf_url!==q.original_sgx_press_release_url||
     x.net_interest_margin_3q26_pct_issuer_reported!=="1.66"||
     x.nonperforming_loan_ratio_pct_issuer_reported!=="0.8"||
     x.cet1_capital_adequacy_ratio_pct_reported!=="15.5"||
     x.return_on_equity_3q26_annualised_pct_reported!=="13.1"||
     x.ratios_are_rounded_public_issuer_values!==true||
     x.exact_table_row_scoping_independently_audited!==false||
     x.independent_numerical_verification!==false||
     x.current_shares_or_market_quote_verified!==false||
     x.per_pbr_ranking_permitted!==false||
     feed.records?.filter(r=>r.symbol==="O39"&&r.ranking_eligible===false).length!==1)
   throw Error("OCBC banking ratios cannot be promoted");
  return {symbol:"O39",nim:x.net_interest_margin_3q26_pct_issuer_reported,
   npl:x.nonperforming_loan_ratio_pct_issuer_reported,
   cet1:x.cet1_capital_adequacy_ratio_pct_reported,
   roe:x.return_on_equity_3q26_annualised_pct_reported,source:x.sgx_primary_pdf_url};
 }
 async function render(){
  const tbody=document.getElementById("ocbcBankRatioRows");
  const status=document.getElementById("ocbcBankRatioStatus");
  if(!tbody||!status)return;
  try{
   const [f,q,r]=await Promise.all(["./data/latest.json",
     "./data/sgx-ocbc-2026q3-bank-profit-v146.json",
     "./data/sgx-ocbc-2026q3-bank-ratios-v149.json"].map(async x=>{
      const response=await fetch(x,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
   }));
   const v=validate(f,q,r);
   tbody.replaceChildren();
   const tr=document.createElement("tr");
   for(const text of ["O39",v.nim+"%",v.npl+"%",v.cet1+"%",v.roe+"%","概数・独立数値検証待ち"]){
    const td=document.createElement("td");td.textContent=text;tr.append(td);
   }
   tbody.append(tr);
   status.textContent="2026年第3四半期のOCBC発行会社資料。CET1は段階適用ベース、ROEは年率表示。2025年度の監査や現在PER/PBRの認証とは別。";
  }catch(err){
   tbody.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="原本の照合が完了していないため非表示";
   tr.append(td);tbody.append(tr);status.textContent="銀行指標の原本確認待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
