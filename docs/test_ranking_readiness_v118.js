"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ranking-readiness-v118.js");
const S=["S68","G13","S20","S63","D05","O39","U11"];
function fixture(){
 const f={schema_version:"value_hunter_web_v29",updated_at_utc:"2026-11-14T05:06:38Z",
  ranking_eligible_count:0,ranking_enabled:false,records:S.map(symbol=>({symbol,ranking_eligible:false}))};
 const a={schema_version:"sgx-ranking-readiness-evidence-v117",ranking_eligible_count:0,
  all_issuers_still_blocked:true,changes_to_financial_feed:false,registered_issuers:7,
  published_feed_updated_at_utc:f.updated_at_utc,records:S.map(symbol=>({
   symbol,sector_model:["D05","O39","U11"].includes(symbol)?"BANKING":"INDUSTRIAL",
   eligible_for_ranking:false,market_cap_or_per_pbr_promoted:false,
   estimated_completion_percentage:null,
   observed_evidence_signals:{issuer_primary_financial_pdf:true},
   remaining_verification_tasks:["financials_independently_checked"]}))};
 return [f,a];
}
assert.equal(validate(...fixture()).length,7);
const changes=[
 ([f,a])=>a.published_feed_updated_at_utc="2026-11-13T00:00:00Z",
 ([f,a])=>a.ranking_eligible_count=1,
 ([f,a])=>a.records[0].eligible_for_ranking=true,
 ([f,a])=>a.records[0].remaining_verification_tasks=["FAKE"],
 ([f,a])=>a.records[0].remaining_verification_tasks=[],
 ([f,a])=>a.records[1].symbol="S68",
 ([f,a])=>f.records[0].ranking_eligible=true,
 ([f,a])=>a.records[0].estimated_completion_percentage=85
];
for(const mutate of changes){const args=fixture();mutate(args);assert.throws(()=>validate(...args));}
console.log("v118 ranking-readiness UI fail-closed checks passed");
