"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./s63-nine-month-v126.js");
function fixture(){
 const f={schema_version:"value_hunter_web_v29",ranking_eligible_count:0,ranking_enabled:false,
   records:[{symbol:"S63",fiscal_year:2025,ranking_eligible:false}]};
 const r={status:"SGX_S63_OFFICIAL_NINE_MONTH_2026_PRESENTATION",
   symbol:"S63",report_date:"2026-11-13",period_end_date:"2026-09-30",
   nine_month_revenue_sgd_billion_rounded:10,nine_month_reported_revenue_yoy_pct:10,
   nine_month_contract_wins_sgd_billion_rounded:13.2,order_book_2026_09_sgd_billion_rounded:37.7,
   audited_income_and_profit_for_new_per_verified:false,
   current_price_or_shares_verified:false,ranking_eligible:false,valuation_recomputed:false,
   source_url:"https://links.sgx.com/FileOpen/test.pdf"};
 return [f,{schema_version:"sgx-s63-9m2026-update-v125",status:r.status,source_url:r.source_url,record:r}];
}
assert.equal(validate(...fixture()).revenueYoY,10);
for(const change of [
 ([f,o])=>o.record.ranking_eligible=true,
 ([f,o])=>o.record.nine_month_revenue_sgd_billion_rounded=11,
 ([f,o])=>o.record.source_url="https://evil.test/file",
 ([f,o])=>o.record.audited_income_and_profit_for_new_per_verified=true,
 ([f,o])=>f.records[0].fiscal_year=2026,
 ([f,o])=>f.ranking_eligible_count=1
]){
 const x=fixture();change(x);assert.throws(()=>validate(...x));
}
console.log("v126 S63 presentation context guard passed");
