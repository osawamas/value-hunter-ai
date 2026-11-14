"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {build,search,quoteViewer}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const paths=["docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json"];
const input=paths.map(read),rows=build(...input);
assert.equal(rows.length,20);
assert.equal(new Set(rows.map(r=>r.code)).size,20);
assert.equal(rows.find(x=>x.code==="O39").kind,"SGX_STATIC");
assert.equal(rows.filter(x=>x.kind==="SGXNET").length,19);
assert.equal(rows.filter(x=>x.warning!==null).length,2);
assert.ok(rows.find(x=>x.code==="5WA").warning.includes("非公開化"));
assert.ok(rows.find(x=>x.code==="P11").warning.includes("再建"));
assert.equal(search(rows,"o39","ALL").length,1);
assert.equal(search(rows," SG1M80907371 ","ALL")[0].code,"579");
assert.equal(search(rows,"healthcare","ALL")[0].code,"5WA");
assert.equal(search(rows,"","CATALIST").every(x=>x.board==="CATALIST"),true);
assert.equal(search(rows,"P11","CATALIST").length,0);
assert.equal(search(rows,"nonexistent","ALL").length,0);
assert.equal(quoteViewer,"https://www.sgx.com/securities/securities-prices?code=stocks");
assert.ok(rows.every(x=>!x.all_current_trading_verified&&!x.financial_or_quote_verified&&!x.ranking_eligible));
for(const edit of [
 a=>{a[0].records[0].trading_code="579"},
 a=>{a[1].records[0].source_url="https://evil.test/bad"},
 a=>{a[1].records[0].ranking_eligible=true},
 a=>{a[2].records[0].current_listing_verified=true},
 a=>{a[2].records[0].code=a[1].records[0].trading_code},
 a=>{a[3].rows.find(x=>x.symbol==="O39").trading_currency="USD"},
 a=>{a[4].events[0].delisted_confirmed=true},
 a=>{a[4].events[0].ranking_eligible=true},
 a=>{a[5].ranking_eligible_count=1}
]){
 const args=input.map(x=>structuredClone(x));edit(args);assert.throws(()=>build(...args));
}
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["sgxHistoricalCodeTitle","sgxHistoricalCodeStatus","sgxHistoricalCodeSearch",
 "sgxHistoricalCodeBoard","sgxHistoricalCodeRows","sgxHistoricalCodeShown"]){
 assert.ok(html.includes('id="'+id+'"'));
}
assert.ok(html.includes('src="./sgx-historical-code-search-v258.js"'));
assert.ok(html.includes(quoteViewer));
console.log("v258 PASS: historical SGX 20-company source-linked search and risk filtering; no licensed quote or ranking promotion");
