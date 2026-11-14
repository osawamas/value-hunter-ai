"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const source=JSON.parse(fs.readFileSync("docs/data/uob-share-display-research-v201.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function verify(x,f){
 assert.equal(x.schema_version,"uob-issuer-share-display-scope-v201");
 assert.equal(x.symbol,"U11");
 assert.equal(x.issuer_microsite.displayed_issued_paid_up_shares,1646915591);
 assert.equal(x.issuer_microsite.exact_share_count_as_of_date_verified,false);
 assert.equal(x.issuer_microsite.quote_redistribution_permission_confirmed,false);
 assert.equal(x.syndicated_sgxnet_buyback.reported_shares_excluding_treasury,1646677591);
 assert.equal(x.syndicated_sgxnet_buyback.source_is_original_sgx_filings,false);
 assert.equal(x.numeric_display_difference_not_reconcilable_due_to_basis_and_dates,
  x.issuer_microsite.displayed_issued_paid_up_shares-x.syndicated_sgxnet_buyback.reported_shares_excluding_treasury);
 assert.equal(x.numeric_display_difference_not_reconcilable_due_to_basis_and_dates,238000);
 assert.equal(x.share_count_definitions_comparable,false);
 assert.equal(x.complete_buyback_chain_verified_as_of_2026_11_13,false);
 assert.equal(x.issuer_page_share_timestamp_verified,false);
 assert.equal(x.original_nov13_sgx_filing_downloaded,false);
 assert.equal(x.market_cap_per_pbr_allowed,false);
 assert.equal(x.ranking_eligible,false);
 assert.equal(x.financial_feed_modified,false);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(f.records.find(r=>r.symbol==="U11").ranking_eligible,false);
 return true;
}
verify(source,feed);
for(const change of [
 (x,f)=>{x.share_count_definitions_comparable=true},
 (x,f)=>{x.issuer_page_share_timestamp_verified=true},
 (x,f)=>{x.original_nov13_sgx_filing_downloaded=true},
 (x,f)=>{x.issuer_microsite.displayed_issued_paid_up_shares++},
 (x,f)=>{x.market_cap_per_pbr_allowed=true},
 (x,f)=>{f.ranking_enabled=true}
]){
 const x=structuredClone(source),f=structuredClone(feed);change(x,f);assert.throws(()=>verify(x,f));
}
console.log("v201 PASS: incompatible UOB share count bases and timestamps cannot enable valuations");
