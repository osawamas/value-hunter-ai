"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {parseCsv,stage}=require("../scripts/stage-sgx-official-directory-v252.js");
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const url="https://www.sgx.com/securities/corporate-information?page=24",date="2026-11-15";
const csv="Trading Code,Trading Name,Listing Board,Traded Currency\n"+
 "O39,\"Oversea-Chinese Banking, Corporation\",MAINBOARD,SGD\n"+
 "H02,Haw Par Corporation,MAINBOARD,SGD\n"+
 "K6S,Prudential PLC,MAINBOARD,USD\n";
const rows=parseCsv("\uFEFF"+csv);
assert.equal(rows.length,4);
assert.equal(rows[1][1],"Oversea-Chinese Banking, Corporation");
function check(args){
 const d=stage(...args);
 assert.equal(d.schema_version,"sgx-manual-official-directory-staging-v252");
 assert.equal(d.staged_security_rows,3);
 assert.equal(d.records.length,3);
 assert.deepEqual(d.records.map(x=>x.symbol),["O39","H02","K6S"]);
 assert.equal(d.records[2].traded_currency,"USD");
 assert.ok(d.staged_not_in_third_party.includes("K6S"));
 assert.equal(d.source_kind,"MANUALLY_SUPPLIED_UNREVIEWED_CSV");
 assert.equal(d.official_full_master_verified,false);
 assert.equal(d.source_license_and_redistribution_authorized,false);
 assert.equal(d.securities_code_coverage_complete,false);
 assert.equal(d.independent_financial_audit_complete,false);
 assert.equal(d.ranking_enabled,false);
 assert.equal(d.ranking_eligible_count,0);
 assert.equal(d.financial_feed_modified,false);
 assert.ok(d.records.every(x=>x.financial_verification===false&&x.ranking_eligible===false));
 return d;
}
check([csv,url,date,candidates,feed]);
for(const bad of [
 x=>{x[0]=x[0].replace("K6S,Prudential","O39,Prudential")},
 x=>{x[0]=x[0].replace("K6S,Prudential","K6S,\"Prudential")},
 x=>{x[0]=x[0].replace("MAINBOARD,USD","INVALID,USD")},
 x=>{x[0]=x[0].replace("K6S,Prudential","K6S,Prudential").replace(",USD",",XYZ")},
 x=>{x[0]=x[0].replace("Trading Code,","Symbol,")},
 x=>{x[0]=x[0].replace("H02,Haw Par Corporation,MAINBOARD,SGD","H02,Haw Par Corporation,MAINBOARD")},
 x=>{x[1]="https://stocks.com.sg/companies"},
 x=>{x[1]="http://www.sgx.com/securities/corporate-information"},
 x=>{x[1]="https://www.sgx.com.evil.test/fake"},
 x=>{x[2]="2026-02-30"},
 x=>{x[3].full_sgx_listing_completeness_verified=true},
 x=>{x[4].ranking_enabled=true},
 x=>{x[4].ranking_eligible_count=1}
]){
 const x=[csv,url,date,structuredClone(candidates),structuredClone(feed)];
 bad(x);assert.throws(()=>stage(...x));
}
assert.throws(()=>parseCsv("A,B\n\"bad\"tail,C"));
assert.throws(()=>parseCsv("A,B\n\"unterminated"));
assert.equal(feed.ranking_eligible_count,0);
console.log("v252 PASS: manual SGX directory CSV staged with source/date gates, safe CSV parsing and zero ranking promotion");
