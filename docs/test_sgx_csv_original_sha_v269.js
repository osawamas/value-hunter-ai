"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof,exportDirectoryCsv,search}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const inputs=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const rows=buildWithOriginalProof(...inputs);
const csv=exportDirectoryCsv(rows);
assert.ok(csv.startsWith("\uFEFF"));
const lines=csv.trim().split("\r\n");
assert.equal(lines.length,31);
assert.match(lines[0],/"originalHtmlSHA256"/);
assert.match(lines[0],/"financialExclusionReasonsJa"/);
for(const r of rows){
 if(r.kind==="SGXNET"){
  assert.match(r.originalHtmlSHA256,/^[a-f0-9]{64}$/);
  assert.ok(csv.includes(r.originalHtmlSHA256));
 } else assert.equal(r.directHtmlIdentityMatched,false);
}
const registered=exportDirectoryCsv(search(rows,"","ALL","REGISTERED"));
assert.equal(registered.trim().split("\r\n").length,5);
assert.throws(()=>exportDirectoryCsv([{...rows.find(x=>x.kind==="SGXNET"),originalHtmlSHA256:null}]));
assert.throws(()=>exportDirectoryCsv([{...rows.find(x=>x.kind==="SGX_STATIC"),directHtmlIdentityMatched:true}]));
assert.throws(()=>exportDirectoryCsv([{...rows[0],ranking_eligible:true}]));
assert.ok(!csv.includes('"price_sgd"'));
console.log("v269 PASS: 19 SGXNet original SHA-256 values and registered financial reason columns exported without any live quote");
