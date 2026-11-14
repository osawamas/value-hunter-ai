"use strict";
const assert=require("node:assert/strict");
const {validateShareWarning}=require("./share-warning-v111.js");
function fixture(){
 const feed={records:[{symbol:"S63",shares_outstanding:3119304988,shares_as_of_date:"2026-06-30"}]};
 const item={schema_version:"sgx-share-snapshot-difference-v110",symbol:"S63",
  new_sgx_primary_announcement_reference:"SG261113OTHRPXGV",
  new_sgx_primary_snapshot_date:"2026-11-13",
  published_reference_is_older:true,current_shares_verified:false,
  price_or_per_pbr_recomputed:false,financial_feed_modified:false,
  ranking_eligible:false,
  published_financial_shares:3119304988,published_financial_record_as_of_date:"2026-06-30",
  new_sgx_primary_issued_ex_treasury:3115847115,new_minus_published_shares:-3457873,
  new_sgx_primary_source_url:"https://links.sgx.com/1.0.0/corporate-announcements/test"};
 return {feed,item};
}
const {feed,item}=fixture();
const warning=validateShareWarning(feed,item);
assert.equal(warning.delta,-3457873);
assert.equal(warning.newShares,3115847115);
const scenarios=[
 x=>x.new_minus_published_shares=0,
 x=>x.current_shares_verified=true,
 x=>x.ranking_eligible=true,
 x=>x.new_sgx_primary_source_url="https://thirdparty.test/SGX",
 x=>x.published_financial_shares=0,
 x=>x.new_sgx_primary_snapshot_date="2026-11-14",
 x=>x.financial_feed_modified=true
];
for(const modify of scenarios){
 const changed=structuredClone(item);modify(changed);
 assert.throws(()=>validateShareWarning(feed,changed));
}
const modified=structuredClone(feed);
modified.records[0].shares_outstanding=3115847115;
assert.throws(()=>validateShareWarning(modified,item));
console.log("v111 share warning fail-closed checks passed");
