"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {build,buildExpanded,search}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const input=[
 "docs/data/sgx-corporate-indexed-page-v253.json",
 "docs/data/sgx-official-issuer-code-filings-v255.json",
 "docs/data/sgx-net-eleven-codes-v256.json",
 "docs/data/sgx-official-batch-seed-v196.json",
 "docs/data/sgx-material-listing-events-v257.json",
 "docs/data/latest.json"
].map(read);
const old=build(...input),all=buildExpanded(...input);
assert.equal(old.length,20);
assert.equal(all.length,30);
assert.equal(new Set(all.map(x=>x.code)).size,30);
assert.equal(search(all,"","UNKNOWN").length,10);
assert.equal(search(all,"","MAINBOARD").length+search(all,"","CATALIST").length,20);
assert.equal(search(all,"U11","ALL")[0].name,"United Overseas Bank Limited");
assert.equal(search(all,"SGX","ALL").some(x=>x.code==="S68"),false); // no fuzzy company alias promotion
assert.equal(search(all,"S68","ALL")[0].kind,"SGX_STATIC");
assert.equal(search(all,"H02","ALL")[0].code,"H02");
assert.equal(search(all,"O39","ALL").length,1);
assert.deepEqual(all.filter(x=>x.board==="UNKNOWN").map(x=>x.code),
 ["D05","G07","H02","C07","J36","BN4","K6S","S68","U11","V03"]);
assert.equal(all.filter(x=>x.warning!==null).length,2);
assert.ok(all.every(x=>x.ranking_eligible===false&&!x.all_current_trading_verified&&!x.financial_or_quote_verified));
for(const mutator of [
 a=>{a[3].rows[0].symbol="O39"},
 a=>{a[3].rows[0].provenance="THIRD_PARTY"},
 a=>{a[3].rows[0].eligible_for_valuation=true},
 a=>{a[3].rows[0].effective_date="2025-10-05"},
 a=>{a[3].rows[0].trading_currency="XXX"},
 a=>{a[3].rows.find(x=>x.symbol==="O39").trading_currency="USD"},
 a=>{a[5].ranking_enabled=true}
]){
 const args=input.map(x=>structuredClone(x));mutator(args);
 assert.throws(()=>buildExpanded(...args));
}
const html=fs.readFileSync("docs/index.html","utf8");
assert.match(html,/SGX公式資料で調べた30銘柄のコード検索/);
assert.match(html,/value="UNKNOWN">市場区分未確認/);
console.log("v259 PASS: 30 distinct SGX sourced historical counters search across partial official sources, still no live rating");
