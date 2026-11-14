"use strict";
const assert=require("node:assert/strict"),{validate}=require("./ocbc-bundle-summary-v167.js");
function fixture(){
 const f={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
 records:[{symbol:"O39",ranking_eligible:false}]};
 const b={schema_version:"sgx-ocbc-bank-research-bundle-v166",symbol:"O39",quarter_end:"2026-09-30",
 sgx_original_pdf_sha256:"a".repeat(64),sgx_original_pdf_url:"https://links.sgx.com/pdf",
 sgx_original_attachment_count:3,multiple_sgx_pdfs_same_issuer_not_independent_financial_verification:true,
 independent_third_party_financial_reperformance:false,"2026_interim_covered_by_fy2025_audit":false,
 current_treasury_shares_verified:false,authenticated_current_exchange_quote_verified:false,
 per_pbr_and_ranking_permitted:false,
 income_statement_sgd_millions:{"3Q26":{group_net_profit:2042,net_interest_income:2313,non_interest_income:1420},
  "9M26":{group_net_profit:6237,allowances_impaired_assets:190,allowances_non_impaired_assets:234,allowances_charged:424}},
 bank_quality_3q26_reported_pct:{cet1_capital_ratio:"15.5",nonperforming_loan_ratio:"0.8"},
 bank_balance_2026_09_30_sgd_millions:{ordinary_equity:60899,equity_attributable_to_bank_equity_holders:63347}};
 return [f,b];
}
assert.equal(validate(...fixture()).profit,2042);
for(const mutate of [
 ([f,b])=>b.current_treasury_shares_verified=true,
 ([f,b])=>b.per_pbr_and_ranking_permitted=true,
 ([f,b])=>b["2026_interim_covered_by_fy2025_audit"]=true,
 ([f,b])=>b.income_statement_sgd_millions["9M26"].allowances_charged=0,
 ([f,b])=>f.ranking_eligible_count=1
]){
 const x=fixture();mutate(x);assert.throws(()=>validate(...x));
}
console.log("v167 bank headline only uses hash-bound issuer research, not market valuations");
