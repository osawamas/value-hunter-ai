"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./annual-arithmetic-v141.js");
function input(){
 const entries=[["G13",9185799,980383,8205416,8205416,0],
                ["S63",16032106,13110861,2921245,2573638,347607]];
 const f={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
   updated_at_utc:"2026-11-14T06:00:00Z",records:[
    ...entries.map(([symbol,assets,liabilities,eq,parent])=>({
      symbol,assets_sgd_thousands:assets,liabilities_sgd_thousands:liabilities,
      equity_sgd_thousands:eq,parent_equity_sgd_thousands:parent,
      ranking_eligible:false,financial_pdf_sha256:"a".repeat(64)})),
    ...["S68","S20","D05","O39","U11"].map(symbol=>({symbol,ranking_eligible:false}))]};
 const a={schema_version:"sgx-annual-statement-arithmetic-v140",
   feed_updated_at_utc:f.updated_at_utc,checked_issuers:2,
   arithmetically_reconciled_count:2,independent_numerical_verification_count:0,
   eligible_count:0,financial_feed_modified:false,
   records:entries.map(([symbol,assets,liabilities,eq,parent,nci])=>({
     symbol,statement_year:2025,unit:"SGD_thousands",assets,liabilities,
     group_equity:eq,parent_attributable_equity:parent,calculated_noncontrolling_interest:nci,
     original_annual_report_sha256:"a".repeat(64),
     same_issuer_audited_statement_arithmetic_passed:true,
     independent_third_party_reperformance_completed:false,
     independent_parent_equity_source_completed:false,
     market_cap_per_pbr_promoted:false,ranking_eligible:false}))};
 return [f,a];
}
assert.equal(validate(...input())[1].minority,347607);
for(const change of [
 ([f,a])=>a.feed_updated_at_utc="stale",
 ([f,a])=>a.records[1].parent_attributable_equity=2921245,
 ([f,a])=>a.records[0].independent_third_party_reperformance_completed=true,
 ([f,a])=>a.records[1].ranking_eligible=true,
 ([f,a])=>f.records[1].ranking_eligible=true,
 ([f,a])=>a.independent_numerical_verification_count=2,
]){
 const x=input();change(x);assert.throws(()=>validate(...x));
}
console.log("v141 audited issuer arithmetic UI verified; no independent valuation claim");
