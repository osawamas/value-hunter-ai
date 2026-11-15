"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {assess}=require("../scripts/assess-sgx-october-release-v292.js");
const {normalize}=require("../scripts/stage-sgx-csv-v199.js");
const release=JSON.parse(fs.readFileSync("docs/data/sgx-october-release-v292.json","utf8"));
let result=assess(release);
assert.equal(result.verdict,"SOURCE_SCOPE_CHECK_PASS");
assert.equal(result.evidence.october_ipo_count,2);
assert.equal(result.evidence.october_ipo_codes_verified,false);
assert.equal(result.evidence.october_listing_count_official_original_verified,false);
assert.equal(result.evidence.august_listing_count_official_original_published,604);
assert.equal(result.evidence.october_secondary_count_reference,605);
assert.equal(result.ranking_eligible_count,0);
function reject(mutator,reason){
 const c=structuredClone(release);mutator(c);
 assert.ok(assess(c).errors.some(x=>x.includes(reason)),reason);
}
reject(x=>{x.sgx_securities_end_oct_2026_reported_605.status="OFFICIAL"},"secondary claim");
reject(x=>{x.original_monthly_statistics_sha256="f".repeat(64)},"fabricated");
reject(x=>{x.issuer_release_ipo_trading_codes=["TEST"]},"invent");
reject(x=>{x.sgx_original_aug_2026_listings.total=605},"august");
reject(x=>{x.ranking_enabled=true},"promote");
reject(x=>{x.issuer_release_confirmed_ipo_count=4},"metadata");
const snapshot=normalize(
 "Trading Code,Trading Name,Traded Currency,Instrument Type\nD05,DBS,SGD,STOCK\n",
 {as_of_date:"2026-10-31",
 source_url:"https://www.sgx.com/securities/securities-prices?code=stocks"});
result=assess(release,snapshot);
assert.equal(result.verdict,"SOURCE_SCOPE_CHECK_PASS");
assert.equal(result.snapshot.comparable_to_official_aug_listing_count,false);
assert.equal(result.snapshot.candidate_rows,1);
console.log("v292 PASS: authentic issuer October announcement scope vs unverified secondary listings and local counter snapshots");
