"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof}=require("./sgx-historical-code-search-v258.js");
const {createDirectory,filterDirectory,toCSV}=require("./sgx-32-research-v296.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const inputs=["sgx-corporate-indexed-page-v253.json","sgx-official-issuer-code-filings-v255.json",
"sgx-net-eleven-codes-v256.json","sgx-official-batch-seed-v196.json",
"sgx-material-listing-events-v257.json","latest.json",
"sgx-nineteen-original-html-sha-v262.json"].map(x=>read("docs/data/"+x));
const prior=buildWithOriginalProof(...inputs);
const ipo=read("docs/data/sgx-october-ipo-listing-v294.json");
const rows=createDirectory(prior,ipo,inputs[5]);
assert.equal(rows.length,32);
assert.equal(new Set(rows.map(x=>x.code)).size,32);
assert.equal(filterDirectory(rows,"","IPO").length,2);
assert.equal(filterDirectory(rows,"","ORIGINAL").length,19);
assert.equal(filterDirectory(rows,"","STATIC").length,11);
assert.equal(filterDirectory(rows,"","ALL","YES").length,4);
assert.deepEqual(filterDirectory(rows,"sgxe96931105").map(x=>x.code),["9DC"]);
assert.deepEqual(filterDirectory(rows,"mim").map(x=>x.code),["MIM"]);
assert.equal(filterDirectory(rows,"not-valid").length,0);
const csv=toCSV(filterDirectory(rows,"","IPO"));
assert.ok(csv.startsWith("\uFEFF"));
assert.ok(csv.includes("SGXE49931863"));
assert.ok(csv.includes("SGXE96931105"));
assert.ok(csv.includes("原本URL"));
assert.equal(csv.includes("ranking_eligible:true"),false);
assert.ok(rows.every(x=>x.rankingEligible===false&&x.activeVerified===false));
for(const bad of [
 (h,i)=>{h[0].code="9DC"},
 (h,i)=>{h[0].financialRankingEligible=true},
 (h,i)=>{h[0].ranking_eligible=true},
 (h,i)=>{i.issuer_listing_confirmations[0].quote_verified=true},
 (h,i)=>{i.issuer_listing_confirmations[1].isin="SGXE00000000"},
 (h,i)=>{i.issuer_listing_confirmations[0].currently_active_listing_verified=true},
 (h,i,f)=>{f.ranking_enabled=true}
]){
 const h=structuredClone(prior),i=structuredClone(ipo),f=structuredClone(inputs[5]);
 bad(h,i,f);assert.throws(()=>createDirectory(h,i,f));
}
const bad=structuredClone(rows);bad[0].rankingEligible=true;
assert.throws(()=>toCSV(bad));
const page=fs.readFileSync("docs/sgx-32-research.html","utf8");
const index=fs.readFileSync("docs/index.html","utf8");
for(const id of ["research32Rows","research32Query","research32Type","research32Finance","research32Export","research32Count","research32Status"])
 assert.ok(page.includes('id="'+id+'"'));
assert.match(page,/sgx-32-research-v296\.js/);
assert.match(page,/sgx-historical-code-search-v258\.js/);
assert.match(index,/href="\.\/sgx-32-research\.html"/);
assert.equal(inputs[5].ranking_eligible_count,0);
console.log("v296 PASS: 32-code Japanese source browser, 19+11+2 scopes, guards, CSV and link");
