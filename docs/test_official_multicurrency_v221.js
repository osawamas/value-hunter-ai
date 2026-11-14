"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const data=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
const {validate}=require("./official-multicurrency-v221.js");
assert.ok(html.includes('src="./official-multicurrency-v221.js"'));
assert.ok(html.includes('id="officialCurrencyPairRows"'));
assert.ok(html.includes('id="officialCurrencyPairStatus"'));
const rows=validate(data,candidates,feed);
assert.deepEqual(rows.map(x=>[x.primary_code,x.secondary_code,x.category]),[
 ["AWX","XWA","POTENTIAL_EQUITY"],["GRN","GRE","ETF"],["EVS","EVD","ETF"]
]);
assert.deepEqual(rows.map(x=>[x.primary_third_party,x.secondary_third_party]),[
 [true,false],[false,false],[false,false]
]);
assert.ok(rows.every(x=>!x.eligible_for_ranking&&!x.independently_verified_as_unique_issuer));
for(const edit of [
 (d,c,f)=>{d.groups[0].counter_pair[1].code="AWX"},
 (d,c,f)=>{d.groups[1].category="POTENTIAL_EQUITY"},
 (d,c,f)=>{d.complete_sgx_list=true},
 (d,c,f)=>{c.candidates.push({symbol:"XWA"})},
 (d,c,f)=>{f.ranking_eligible_count++}
]){
 const d=structuredClone(data),c=structuredClone(candidates),f=structuredClone(feed);
 edit(d,c,f);assert.throws(()=>validate(d,c,f));
}
console.log("v221 PASS: official SGX currency-pair display remains separate from issuers and third-party ranked securities");
