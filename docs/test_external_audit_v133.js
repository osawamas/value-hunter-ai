"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./external-audit-v133.js");
function fixture(){
 const symbols=["G13","S63"];
 const feed={schema_version:"value_hunter_web_v29",updated_at_utc:"2026-11-14T00:00:00Z",
  ranking_eligible_count:0,ranking_enabled:false,records:[
   ...symbols.map(symbol=>({symbol,fiscal_year:2025,ranking_eligible:false,
    financial_source_url:"https://links.sgx.com/annual/"+symbol,financial_pdf_sha256:"a".repeat(64)})),
   ...["S68","S20","D05","O39","U11"].map(symbol=>({symbol,ranking_eligible:false}))
  ]};
 const a={schema_version:"sgx-fy2025-audit-assurance-v132",
  linked_published_feed_updated_at_utc:feed.updated_at_utc,
  external_auditor_fy2025_opinion_confirmed_count:2,
  numeric_recalculation_completed_count:0,ranking_eligible_count:0,
  financial_feed_modified:false,external_auditor_opinion_is_not_live_market_verification:true,
  records:symbols.map(symbol=>({
   symbol,fiscal_year:2025,independent_external_audit_opinion_observed:true,
   auditor:"PricewaterhouseCoopers LLP",auditor_scope_end:"2025-12-31",
   annual_report_primary_source_url:"https://links.sgx.com/annual/"+symbol,
   annual_report_primary_sha256:"a".repeat(64),
   reperformed_independent_financial_calculations:false,
   "2026_interim_audited_by_same_fy2025_opinion":false,
   current_shares_and_quote_independently_verified:false,
   parent_equity_independently_reperformed:false,eligible_for_ranking:false
  }))};
 return [feed,a];
}
assert.equal(validate(...fixture()).length,2);
for(const change of [
 ([f,a])=>a.linked_published_feed_updated_at_utc="yesterday",
 ([f,a])=>a.records[0].current_shares_and_quote_independently_verified=true,
 ([f,a])=>a.records[1].auditor="UNKNOWN",
 ([f,a])=>a.records[0].fiscal_year=2026,
 ([f,a])=>a.records[0].annual_report_primary_sha256="b".repeat(64),
 ([f,a])=>a.numeric_recalculation_completed_count=2,
 ([f,a])=>f.ranking_eligible_count=1
]){
 const z=fixture();change(z);assert.throws(()=>validate(...z));
}
console.log("v133 FY2025 auditor UI guards passed");
