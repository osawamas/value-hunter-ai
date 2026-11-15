"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof,search}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const files=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"
].map(read);
const result=buildWithOriginalProof(...files);
assert.equal(result.length,30);
assert.equal(result.filter(x=>x.directHtmlIdentityMatched).length,19);
assert.equal(result.filter(x=>!x.directHtmlIdentityMatched).length,11);
assert.equal(new Set(result.map(x=>x.code)).size,30);
assert.equal(result.find(x=>x.code==="O39").directHtmlIdentityMatched,false);
assert.equal(result.find(x=>x.code==="579").directHtmlIdentityMatched,true);
assert.equal(result.find(x=>x.code==="HQU").originalHtmlSHA256.length,64);
assert.equal(result.find(x=>x.code==="P11").directHtmlIdentityMatched,true);
assert.ok(result.find(x=>x.code==="P11").warning);
assert.equal(search(result,"O39","ALL").length,1);
assert.ok(result.every(x=>!x.all_current_trading_verified&&!x.ranking_eligible));
for(const mutator of [
 x=>{x[6].records[0].original_html_sha256="0".repeat(63)},
 x=>{x[6].records[0].original_html_bytes=0},
 x=>{x[6].records[0].name="FAKE COMPANY"},
 x=>{x[6].records[0].url="https://evil.test"},
 x=>{x[6].records[0].isin="SG1BAD"},
 x=>{x[6].records[0].ref="BADREF"},
 x=>{x[6].records[0].required_name_code_isin_reference_found=false},
 x=>{x[6].records[0].ranking_eligible=true},
 x=>{x[6].records[1].code=x[6].records[0].code},
 x=>{x[6].records.pop()},
 x=>{x[6].matching_original_html_count=18},
 x=>{x[6].replay_job_id=123},
 x=>{x[6].market_quote_licence_verified=true},
 x=>{x[5].ranking_eligible_count=1}
]){
 const a=files.map(x=>structuredClone(x));mutator(a);
 assert.throws(()=>buildWithOriginalProof(...a));
}
const script=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
assert.match(script,/sgx-nineteen-original-html-sha-v262\.json/);
assert.match(script,/SGXNet原本HTMLの直接再取得で19銘柄/);
assert.match(script,/buildWithOriginalProof\(\.\.\.files\)/);
console.log("v262 PASS: 19 actual SGXNet original HTML digests permanently mapped to source codes, 11 static securities held distinct; rankings blocked");
