"use strict";
const assert=require("node:assert/strict");
const {normalize}=require("../scripts/stage-sgx-csv-v199.js");
const {inspect}=require("../scripts/classify-sgx-counters-v202.js");
const asof="2026-11-14",source="https://www.sgx.com/securities/securities-prices?code=stocks";
const csv=[
 "Trading Code,Trading Name,Traded Currency,Security Type,Listing Board,Last,Bid,Ask,Volume",
 "D05,DBS,SGD,STOCK,MAINBOARD,70.00,69.99,70.01,10000",
 "ZZ1,Test REIT,SGD,REIT,MAINBOARD,1.20,1.19,1.21,100",
 "AAA,Test ETF,USD,ETF,MAINBOARD,4.10,4.00,4.20,100",
 "ZZ2,Test Warranty,SGD,STRUCTURED WARRANT,MAINBOARD,0.01,0.01,0.02,100",
 "ZZ3,Unknown Counter,USD,,CATALIST,2.00,1.90,2.10,100"
].join("\n");
const staged=normalize(csv,{as_of_date:asof,source_url:source});
const classified=inspect(staged);
assert.equal(staged.item_count,5);
assert.equal(classified.total_counters,5);
assert.equal(classified.counts.POTENTIAL_EQUITY,1);
assert.equal(classified.counts.REIT,1);
assert.equal(classified.counts.ETF,1);
assert.equal(classified.counts.WARRANT,1);
assert.equal(classified.counts.UNCLASSIFIED,1);
assert.equal(classified.candidate_equity_counters_not_verified_issuers,1);
assert.ok(classified.rows.every(x=>x.ranking_eligible===false));
assert.ok(staged.items.every(x=>!Object.keys(x).some(k=>/price|last|bid|ask|volume/i.test(k))));
assert.ok(staged.full_sgx_universe_verified===false);
assert.ok(staged.licensed_quote_access===false);
// Staged identities may be valid but cannot be promoted by flipping evidence switches.
for(const mutate of [
 (x)=>{x.original_file_is_sgx_verified=true},
 (x)=>{x.ranking_enabled=true},
 (x)=>{x.licensed_quote_access=true},
 (x)=>{x.items[1].instrument_type="STOCK";x.item_count++}
]){
 const x=structuredClone(staged);mutate(x);assert.throws(()=>inspect(x));
}
console.log("v203 PASS: manual SGX CSV normalizes, strips market prices, classifies instrument types, and stays unverified");
