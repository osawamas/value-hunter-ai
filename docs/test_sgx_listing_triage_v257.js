"use strict";
const assert=require("node:assert/strict");
const {build}=require("../scripts/triage-sgx-listing-v257.js");
const r=build();
assert.equal(r.total,20);
assert.equal(r.high_priority,6);
assert.equal(r.verified_current_listings,0);
assert.equal(r.confirmed_delistings,0);
assert.equal(r.licensed_quotes,0);
assert.equal(r.ranking_eligible_count,0);
assert.equal(new Set(r.records.map(x=>x.code)).size,20);
for(const code of ["P11","5WA","5SY","VC2","43A","TS0U"]){
 const x=r.records.find(x=>x.code===code);
 assert.equal(x.review_priority,"HIGH");
 assert.equal(x.current_listing_verified,false);
 assert.equal(x.delisted_verified,false);
 assert.equal(x.ranking_eligible,false);
}
assert.ok(r.records.every(x=>x.quote_verified===false));
console.log("v257 PASS: six corporate-action review priorities without listing, quote or ranking promotion");
