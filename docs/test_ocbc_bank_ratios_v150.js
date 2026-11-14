"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ocbc-bank-ratios-v150.js");
function fixture(){
 const f={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
   records:[{symbol:"O39",ranking_eligible:false}]};
 const source="https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/910569_OCBC_3Q26_Results_Press_Release.pdf";
 const q={schema_version:"sgx-ocbc-q3-metrics-probe-v146",
  status:"OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED",
  record:{original_sgx_press_release_url:source,original_sgx_pdf_sha256:"a".repeat(64)}};
 const r={schema_version:"sgx-ocbc-bank-ratio-probe-v149",
  status:"OCBC_3Q26_ISSUER_BANK_RATIOS_OBSERVED_IN_PRIMARY_PDF",
  record:{schema_version:"sgx-ocbc-3q26-bank-ratio-research-v149",symbol:"O39",
   financial_period_end:"2026-09-30",sgx_primary_pdf_sha256:"a".repeat(64),
   sgx_primary_pdf_url:source,net_interest_margin_3q26_pct_issuer_reported:"1.66",
   nonperforming_loan_ratio_pct_issuer_reported:"0.8",
   cet1_capital_adequacy_ratio_pct_reported:"15.5",
   return_on_equity_3q26_annualised_pct_reported:"13.1",
   ratios_are_rounded_public_issuer_values:true,
   exact_table_row_scoping_independently_audited:false,
   independent_numerical_verification:false,
   current_shares_or_market_quote_verified:false,per_pbr_ranking_permitted:false}};
 return [f,q,r];
}
assert.equal(validate(...fixture()).cet1,"15.5");
for(const change of [
 ([f,q,r])=>r.record.independent_numerical_verification=true,
 ([f,q,r])=>r.record.per_pbr_ranking_permitted=true,
 ([f,q,r])=>r.record.sgx_primary_pdf_sha256="b".repeat(64),
 ([f,q,r])=>r.record.net_interest_margin_3q26_pct_issuer_reported="16.6",
 ([f,q,r])=>f.records[0].ranking_eligible=true,
 ([f,q,r])=>f.ranking_eligible_count=1
]){
 const x=fixture();change(x);assert.throws(()=>validate(...x));
}
console.log("v150 OCBC original bank-quality evidence UI checks passed");
