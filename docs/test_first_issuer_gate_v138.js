"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./first-issuer-gate-v138.js");
const keys=["fy2025_external_auditor_opinion","parent_equity_independent_reperformance",
"financial_numerical_independent_reperformance","authenticated_sgx_execution_quote",
"authenticated_quote_exact_trade_time","latest_treasury_adjusted_shares",
"quote_share_effective_date_compatible","current_earnings_period_applicable"];
function fixture(){
 const f={schema_version:"value_hunter_web_v29",updated_at_utc:"2026-11-14T06:00:00Z",
   ranking_enabled:false,ranking_eligible_count:0,records:["G13","S63"].map(symbol=>({symbol,ranking_eligible:false}))};
 const g={schema_version:"sgx-first-issuer-evidence-gate-v137",
  feed_updated_at_utc:f.updated_at_utc,checked_issuers:2,
  eligible_count:0,ranking_activation_permitted:false,no_financial_feed_changes:true,
  required_evidence_fields:[...keys],
  records:["G13","S63"].map(symbol=>({symbol,eligible_for_ranking:false,
   promoted_market_cap_per_pbr:false,historical_share_snapshot_is_not_current:true,
   evidence_requirements:Object.fromEntries(keys.map(k=>[k,k==="fy2025_external_auditor_opinion"])),
   unmet_requirements:keys.slice(1)}))};
 return [f,g];
}
assert.equal(validate(...fixture()).length,2);
for(const change of [
 ([f,g])=>g.feed_updated_at_utc="old",
 ([f,g])=>g.records[0].evidence_requirements.authenticated_sgx_execution_quote=true,
 ([f,g])=>g.records[1].eligible_for_ranking=true,
 ([f,g])=>g.records[0].unmet_requirements=[],
 ([f,g])=>g.records[0].evidence_requirements.fake=true,
 ([f,g])=>f.ranking_eligible_count=1
]){
 const input=fixture();change(input);assert.throws(()=>validate(...input));
}
console.log("v138 strict ranking checklist display OK");
