"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ocbc-quarter-v147.js");
function fixture(){
 const f={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
   records:[{symbol:"O39",ranking_eligible:false}]};
 const o={schema_version:"sgx-ocbc-q3-metrics-probe-v146",status:"OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED",
 record:{schema_version:"sgx-ocbc-3q26-official-bank-results-v146",
 symbol:"O39",period_end_date:"2026-09-30",financial_type:"BANK",
 group_net_profit_3q26_sgd_billion_reported:"2.04",
 group_net_profit_9m26_sgd_billion_reported:"6.24",
 group_net_profit_3q26_yoy_pct_reported:3,
 group_net_profit_9m26_yoy_pct_reported:10,
 reported_values_are_rounded_in_original_release:true,
 independent_third_party_earnings_verification:false,
 quarter_is_audited_annual_2025:false,annualised_per_calculated:false,
 exact_sgx_execution_quote_verified:false,current_treasury_adjusted_shares_verified:false,
 ranking_eligible:false,original_sgx_press_release_url:
 "https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/910569_OCBC_3Q26_Results_Press_Release.pdf",
 original_sgx_pdf_sha256:"a".repeat(64)}};
 return [f,o];
}
assert.equal(validate(...fixture()).profitQuarter,"2.04");
for(const change of [
 ([f,o])=>o.record.independent_third_party_earnings_verification=true,
 ([f,o])=>o.record.annualised_per_calculated=true,
 ([f,o])=>o.record.group_net_profit_3q26_sgd_billion_reported="20.4",
 ([f,o])=>o.record.original_sgx_press_release_url="https://fake.example/file.pdf",
 ([f,o])=>f.ranking_eligible_count=1
]){
 const x=fixture();change(x);assert.throws(()=>validate(...x));
}
console.log("v147 OCBC bank-only unaudited reference UI guard passed");
