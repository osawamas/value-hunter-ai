"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const {derive}=require("../scripts/build-bank-evidence-readiness-v243.js");
const source=[
 "docs/data/sgx-uob-official-buyback-v242.json",
 "docs/data/sgx-bank-corporate-actions-v190.json",
 "docs/data/sgx-source-rights-review-v222.json",
 "docs/data/latest.json"
].map(p=>JSON.parse(fs.readFileSync(p,"utf8")));
function verify(args){
 const result=derive(...args);
 assert.equal(result.schema_version,"sgx-bank-share-evidence-decision-v243");
 assert.equal(result.source_consistency_passed,true,"must fail closed on source mismatch");
 assert.equal(result.ranking_eligible_count,0);
 assert.equal(result.rankings_enabled,false);
 assert.equal(result.licensed_timestamped_quote_verified,false);
 assert.equal(result.redistribution_rights_verified,false);
 assert.equal(result.independent_financial_audit_verified,false);
 assert.equal(result.feed_modified,false);
 assert.equal(result.banks.length,2);
 const [u,o]=result.banks;
 assert.equal(u.symbol,"U11");assert.equal(o.symbol,"O39");
 assert.equal(u.verified_historical_share_snapshot,true);
 assert.equal(u.historical_as_of_date,"2026-11-12");
 assert.equal(u.historical_ex_treasury_shares,1646711591);
 assert.equal(u.latest_nov13_official_original_obtained,false);
 assert.equal(u.secondary_nov13_included,false);
 assert.equal(o.original_attachment_verified,false);
 assert.equal(o.original_numeric_share_change_verified,false);
 assert.equal(o.historical_ex_treasury_shares,null);
 assert.ok(result.blockers.includes("OCBC_NOV12_ORIGINAL_PDF_NOT_VERIFIED"));
 assert.ok(result.blockers.includes("UOB_NOV13_OFFICIAL_ORIGINAL_NOT_VERIFIED"));
 for(const x of result.banks){assert.equal(x.live_valuation_allowed,false);assert.equal(x.ranking_eligible,false)}
}
verify(source);
for(const edit of [
 a=>{a[0].rows[2].issued_excluding_treasury_after_purchase++},
 a=>{a[0].rows[2].announcement_ref="CHANGED"},
 a=>{a[0].official_current_asof_date="2026-11-13"},
 a=>{a[1].verified_as_of_date="2026-11-13"},
 a=>{a[1].uob.observations[1].source_url="https://thirdparty.example"},
 a=>{a[1].uob.latest_unverified.official_verified=true},
 a=>{a[1].ocbc.outstanding_change_notice.official_attachment_obtained=true},
 a=>{a[1].ocbc.outstanding_change_notice.may_enter_ranking=true},
 a=>{a[2].licensed_time_stamped_quote_available=true},
 a=>{a[2].feeds[0].public_quote_redistribution_authorized=true},
 a=>{a[3].ranking_enabled=true},
 a=>{a[3].ranking_eligible_count=1}
]){
 const args=source.map(x=>structuredClone(x));edit(args);
 assert.throws(()=>verify(args));
}
console.log("v243 PASS: derived UOB date-bound shares, OCBC pending original and licensed market data fail-closed");
