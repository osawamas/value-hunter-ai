"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./g13-quarter-warning-v123.js");
function fixture(){
 const feed={schema_version:"value_hunter_web_v29",ranking_enabled:false,
  ranking_eligible_count:0,records:[{symbol:"G13",ranking_eligible:false,
  fiscal_year:2025,attributable_profit_sgd_thousands:390346}]};
 const q={schema_version:"sgx-g13-2026q3-original-v121",
  status:"SGX_PRIMARY_2026Q3_UNAUDITED_BUSINESS_UPDATE",record:{
   status:"SGX_PRIMARY_2026Q3_UNAUDITED_BUSINESS_UPDATE",
   quarter_end_date:"2026-09-30",revenue_2026q3_sgd_thousands:566096,
   revenue_2025q3_sgd_thousands:649790,
   net_profit_after_tax_2026q3_sgd_thousands:54731,
   net_profit_after_tax_2025q3_sgd_thousands:94618,
   revenue_yoy_pct:-12.88,net_profit_yoy_pct:-42.16,
   financials_audited:false,financials_reviewed:false,
   older_fy_per_cannot_be_described_as_current:true,
   ranking_eligible:false,annual_profit_period_compatible_for_repricing:false,
   source_url:"https://links.sgx.com/FileOpen/test.ashx?App=Announcement&FileID=911200"
  }};
 return [feed,q];
}
assert.equal(validate(...fixture()).revenueYoY,-12.88);
for(const change of [
 ([f,q])=>q.record.financials_audited=true,
 ([f,q])=>q.record.ranking_eligible=true,
 ([f,q])=>q.record.source_url="https://untrusted.example",
 ([f,q])=>q.record.revenue_2026q3_sgd_thousands=100,
 ([f,q])=>f.records[0].attributable_profit_sgd_thousands=1,
 ([f,q])=>f.records[0].fiscal_year=2026,
 ([f,q])=>f.ranking_eligible_count=1
]){
 const x=fixture();change(x);assert.throws(()=>validate(...x));
}
console.log("v123 quarterly warning regression OK");
